"""Seed script for users."""

from sqlalchemy import select
from app.models.core import User, Role, UserRole, Organization
from app.core.security import get_password_hash


async def seed_users(session):
    """Insert default admin user with roles into the database."""
    # Get default organization
    org = (await session.execute(select(Organization))).scalar_one()

    # Get roles
    role_owner = (
        await session.execute(select(Role).where(Role.code == "owner"))
    ).scalar_one()
    role_admin = (
        await session.execute(select(Role).where(Role.code == "admin"))
    ).scalar_one()

    # Create admin user
    admin_data = {
        "email": "admin@sme.com",
        "full_name": "Administrator",
        "password_hash": get_password_hash("123456"),  # Password = 123456
        "org_id": org.id,
        "status": "active",
    }

    existing_user = await session.execute(
        select(User).where(User.email == admin_data["email"])
    )
    user = existing_user.scalar_one_or_none()

    if not user:
        user = User(**admin_data)
        session.add(user)
        await session.flush()  # Need flush to get user.id
        print("[seed] Created admin user (email: admin@sme.com, password: 123456)")
    else:
        print("[seed] Admin user already exists, skipping")

    # Assign both roles: owner + admin
    existing_owner_role = await session.execute(
        select(UserRole).where(
            (UserRole.user_id == user.id)
            & (UserRole.role_id == role_owner.id)
            & (UserRole.org_id == org.id)
        )
    )
    if not existing_owner_role.scalar_one_or_none():
        session.add(UserRole(user_id=user.id, role_id=role_owner.id, org_id=org.id))
        print("[seed] Assigned role Owner to admin user")

    existing_admin_role = await session.execute(
        select(UserRole).where(
            (UserRole.user_id == user.id)
            & (UserRole.role_id == role_admin.id)
            & (UserRole.org_id == org.id)
        )
    )
    if not existing_admin_role.scalar_one_or_none():
        session.add(UserRole(user_id=user.id, role_id=role_admin.id, org_id=org.id))
        print("[seed] Assigned role Admin to admin user")
