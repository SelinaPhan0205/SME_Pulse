"""Trình chạy seed chính - thực thi tất cả các seed theo đúng thứ tự."""

import asyncio
from app.db.session import AsyncSessionLocal
from app.db.seeds.seed_roles import seed_roles
from app.db.seeds.seed_organizations import seed_organizations
from app.db.seeds.seed_users import seed_users
from app.db.seeds.seed_customers_suppliers import seed_customers_suppliers
from app.db.seeds.seed_accounts import seed_accounts


async def run_all_seeds():
    """Chạy tất cả các hàm seed theo thứ tự."""
    async with AsyncSessionLocal() as session:
        try:
            print("\n🌱 Starting database seed...\n")
            
            await seed_roles(session)
            await seed_organizations(session)
            await seed_users(session)
            await seed_customers_suppliers(session)
            await seed_accounts(session)

            await session.commit()
            
            print("\n" + "="*60)
            print("🎉 SEED COMPLETED SUCCESSFULLY!")
            print("="*60)
            print("\n✅ Test Login Credentials:")
            print("   Email: admin@sme.com")
            print("   Password: 123456")
            print("   Roles: Owner, System Administrator")
            print("\n")
        except Exception as e:
            await session.rollback()
            print(f"\n❌ SEED FAILED: {str(e)}\n")
            raise


if __name__ == "__main__":
    asyncio.run(run_all_seeds())
