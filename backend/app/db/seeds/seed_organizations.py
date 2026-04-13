"""Kịch bản seed cho các tổ chức."""

from sqlalchemy import select
from app.models.core import Organization


async def seed_organizations(session):
    """Chèn tổ chức mặc định vào cơ sở dữ liệu."""
    default_org = {
        "name": "SME Demo Company",
        "tax_code": "1234567890",
        "address": "Ho Chi Minh City, Vietnam",
    }

    existing = await session.execute(
        select(Organization).where(Organization.tax_code == default_org["tax_code"])
    )
    org = existing.scalar_one_or_none()

    if not org:
        session.add(Organization(**default_org))
        await session.flush()  # Flush để làm cho nó khả dụng cho các truy vấn tiếp theo
        print("[seed] Created default organization")
    else:
        print("[seed] Organization already exists, skipping")
