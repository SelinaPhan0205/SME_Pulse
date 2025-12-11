"""Quick script to fix admin password."""
import asyncio
from app.db.session import AsyncSessionLocal
from app.core.security import get_password_hash
from sqlalchemy import text

async def fix_password():
    async with AsyncSessionLocal() as db:
        password_hash = get_password_hash("admin123")
        print(f"Generated hash: {password_hash}")
        
        await db.execute(
            text("UPDATE core.users SET password_hash = :hash WHERE email = :email"),
            {"hash": password_hash, "email": "admin@sme.com"}
        )
        await db.commit()
        print("✓ Password updated successfully!")

if __name__ == "__main__":
    asyncio.run(fix_password())
