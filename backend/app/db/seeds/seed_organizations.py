"""Seed script for organizations."""

from sqlalchemy import select
from app.models.core import Organization


async def seed_organizations(session):
    """Insert default organization into the database."""
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
        await session.flush()  # Flush to make it available for subsequent queries
        print("[seed] Created default organization")
    else:
        print("[seed] Organization already exists, skipping")
