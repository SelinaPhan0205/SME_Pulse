"""Seed script for customers and suppliers."""

from sqlalchemy import select
from app.models.core import Customer, Supplier, Organization


async def seed_customers_suppliers(session):
    """Insert sample customers and suppliers into the database."""
    org = (await session.execute(select(Organization))).scalar_one()

    customers = [
        {
            "code": "CUS001",
            "name": "Nguyen_Van_A",
            "tax_code": "1111111111",
            "credit_term": 30,
            "org_id": org.id,
        },
        {
            "code": "CUS002",
            "name": "Nguyen_Thi_B",
            "tax_code": "2222222222",
            "credit_term": 45,
            "org_id": org.id,
        },
    ]

    suppliers = [
        {
            "code": "SUP001",
            "name": "Nguyen_Van_C",
            "tax_code": "3333333333",
            "payment_term": 30,
            "org_id": org.id,
        },
        {
            "code": "SUP002",
            "name": "UIT Tech",
            "tax_code": "4444444444",
            "payment_term": 15,
            "org_id": org.id,
        },
    ]

    # Insert customers
    for c in customers:
        exists = await session.execute(
            select(Customer).where(Customer.code == c["code"])
        )
        if not exists.scalar_one_or_none():
            session.add(Customer(**c))
            print(f"[seed] Inserted customer {c['code']}")

    # Insert suppliers
    for s in suppliers:
        exists = await session.execute(
            select(Supplier).where(Supplier.code == s["code"])
        )
        if not exists.scalar_one_or_none():
            session.add(Supplier(**s))
            print(f"[seed] Inserted supplier {s['code']}")
