"""Kịch bản seed cho các tài khoản."""

from sqlalchemy import select
from app.models.core import Account, Organization


async def seed_accounts(session):
    """Chèn các tài khoản mẫu (tiền mặt và ngân hàng) vào cơ sở dữ liệu."""
    org = (await session.execute(select(Organization))).scalar_one()

    accounts = [
        {"name": "Cash Drawer", "type": "cash", "org_id": org.id},
        {
            "name": "VCB Main Bank",
            "type": "bank",
            "account_number": "0123456789",
            "bank_name": "Vietcombank",
            "org_id": org.id,
        },
    ]

    for acc in accounts:
        exists = await session.execute(
            select(Account).where(Account.name == acc["name"])
        )
        if not exists.scalar_one_or_none():
            session.add(Account(**acc))
            print(f"[seed] Inserted account {acc['name']}")
