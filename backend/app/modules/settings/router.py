"""Settings router - Organization settings API."""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.core import User, Organization
from app.modules.auth.dependencies import get_current_user
from app.schema.core.organization import OrganizationSettings, OrganizationSettingsUpdate

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/settings", response_model=OrganizationSettings)
async def get_organization_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current organization settings.
    
    **Protected endpoint - requires authentication**
    
    Returns settings for the user's organization (multi-tenant).
    
    Args:
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        Organization settings
    
    Raises:
        HTTPException 404: Organization not found
    """
    # Get organization for current user
    stmt = select(Organization).where(Organization.id == current_user.org_id)
    result = await db.execute(stmt)
    org = result.scalar_one_or_none()
    
    if not org:
        logger.error(f"Organization {current_user.org_id} not found for user {current_user.id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    logger.info(f"Retrieved settings for organization {org.id}")
    
    return OrganizationSettings.model_validate(org)


@router.put("/settings", response_model=OrganizationSettings)
async def update_organization_settings(
    updates: OrganizationSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update current organization settings.
    
    **Protected endpoint - requires Owner/Admin role**
    
    Args:
        updates: Settings to update
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        Updated organization settings
    
    Raises:
        HTTPException 403: Insufficient permissions (not Owner/Admin)
        HTTPException 404: Organization not found
    """
    # RBAC check: Only Owner/Admin can update settings
    user_roles = [ur.role.code for ur in current_user.roles if ur.role]
    if not any(role in ['owner', 'admin'] for role in user_roles):
        logger.warning(f"User {current_user.id} attempted to update settings without permission")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Owner/Admin can update organization settings"
        )
    
    # Get organization
    stmt = select(Organization).where(Organization.id == current_user.org_id)
    result = await db.execute(stmt)
    org = result.scalar_one_or_none()
    
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    # Update fields
    update_data = updates.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(org, field, value)
    
    await db.commit()
    await db.refresh(org)
    
    logger.info(f"Updated settings for organization {org.id}")
    
    return OrganizationSettings.model_validate(org)
