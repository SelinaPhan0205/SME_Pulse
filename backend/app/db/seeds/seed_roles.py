"""Seed script for roles."""

from sqlalchemy import select
from app.models.core import Role


async def seed_roles(session):
    """Insert default roles into the database."""
    roles = [
        {"code": "owner", "name": "Owner"},
        {"code": "accountant", "name": "Accountant"},
        {"code": "cashier", "name": "Cashier"},
        {"code": "admin", "name": "System Administrator"},
    ]

    for role_data in roles:
        existing = await session.execute(
            select(Role).where(Role.code == role_data["code"])
        )
        role = existing.scalar_one_or_none()

        if not role:
            session.add(Role(**role_data))
            print(f"[seed] Inserted role: {role_data['code']}")
        else:
            print(f"[seed] Role {role_data['code']} already exists, skipping")
    
    await session.flush()  # Flush to make all roles available for subsequent queries
