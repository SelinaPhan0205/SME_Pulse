"""Router Cài đặt - API cài đặt tổ chức."""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.core import User, Organization
from app.modules.auth.dependencies import get_current_user, requires_roles
from app.schema.core.organization import OrganizationSettings, OrganizationSettingsUpdate

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/settings", response_model=OrganizationSettings)
async def get_organization_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Lấy cài đặt tổ chức hiện tại.
    
    **Điểm cuối bảo vệ - yêu cầu xác thực**
    
    Trả về cài đặt cho tổ chức của người dùng (multi-tenant).
    
    Tham số:
        current_user: Người dùng được xác thực hiện tại
        db: Phiên cơ sở dữ liệu
    
    Trả về:
        Cài đặt tổ chức
    
    Tăng:
        HTTPException 404: Tổ chức không được tìm thấy
    """
    # Lấy tổ chức cho người dùng hiện tại
    stmt = select(Organization).where(Organization.id == current_user.org_id)
    result = await db.execute(stmt)
    org = result.scalar_one_or_none()
    
    if not org:
        logger.error(f"Organization {current_user.org_id} not found for user {current_user.id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tổ chức không được tìm thấy"
        )
    
    logger.info(f"Retrieved settings for organization {org.id}")
    
    return OrganizationSettings.model_validate(org)


@router.put("/settings", response_model=OrganizationSettings)
async def update_organization_settings(
    updates: OrganizationSettingsUpdate,
    current_user: User = Depends(requires_roles(["owner", "admin"])),
    db: AsyncSession = Depends(get_db)
):
    """
    Cập nhật cài đặt tổ chức hiện tại.
    
    **Điểm cuối bảo vệ - yêu cầu vai trò Chủ sở/Quản trị viên**
    
    Tham số:
        updates: Cài đặt cần cập nhật
        current_user: Người dùng được xác thực hiện tại
        db: Phiên cơ sở dữ liệu
    
    Trả về:
        Cài đặt tổ chức được cập nhật
    
    Tăng:
        HTTPException 403: Không đủ quyền (không phải Chủ sở/Quản trị viên)
        HTTPException 404: Tổ chức không được tìm thấy
    """
    # Lấy tổ chức
    stmt = select(Organization).where(Organization.id == current_user.org_id)
    result = await db.execute(stmt)
    org = result.scalar_one_or_none()
    
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tổ chức không được tìm thấy"
        )
    
    # Cập nhật các trường
    update_data = updates.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(org, field, value)
    
    await db.commit()
    await db.refresh(org)
    
    logger.info(f"Updated settings for organization {org.id}")
    
    return OrganizationSettings.model_validate(org)
