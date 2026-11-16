import uuid
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select

from backend.app.core.database import SessionLocal
from backend.app.models.customer import Customer
from backend.app.models.order import Order


SEED_NAMESPACE = uuid.UUID("0a02f1d8-6ec5-4ffc-a9ab-e9d1a936d9e2")


def stable_id(value: str) -> uuid.UUID:
    return uuid.uuid5(SEED_NAMESPACE, value)


def customer_rows() -> list[dict]:
    return [
        {
            "id": stable_id(f"customer-{number}"),
            "name": f"Demo Customer {number:02d}",
            "email": f"demo.customer{number:02d}@shopease.example",
        }
        for number in range(1, 21)
    ]


def order_rows(customers: list[dict]) -> list[dict]:
    customer_by_number = {
        number: customers[number - 1]["id"] for number in range(1, 21)
    }
    rows = [
        {
            "id": stable_id("order-SE1025"),
            "order_number": "SE1025",
            "customer_id": customer_by_number[1],
            "product": "Sony headphones",
            "category": "electronics",
            "quantity": 1,
            "total_amount": Decimal("129.99"),
            "currency": "USD",
            "order_status": "delivered",
            "payment_status": "paid",
            "payment_method": "card",
            "payment_reference": "PAY-SE1025",
            "order_date": date(2026, 10, 1),
            "shipping_date": date(2026, 10, 2),
            "delivery_date": date(2026, 10, 5),
        },
        {
            "id": stable_id("order-SE1026"),
            "order_number": "SE1026",
            "customer_id": customer_by_number[2],
            "product": "Travel backpack",
            "category": "accessories",
            "quantity": 1,
            "total_amount": Decimal("74.50"),
            "currency": "USD",
            "order_status": "shipped",
            "payment_status": "paid",
            "payment_method": "card",
            "payment_reference": "PAY-SE1026",
            "order_date": date(2026, 11, 1),
            "shipping_date": date(2026, 11, 2),
            "delivery_date": None,
        },
        {
            "id": stable_id("order-SE1027"),
            "order_number": "SE1027",
            "customer_id": customer_by_number[3],
            "product": "Wireless keyboard",
            "category": "electronics",
            "quantity": 1,
            "total_amount": Decimal("59.00"),
            "currency": "USD",
            "order_status": "cancelled",
            "payment_status": "refunded",
            "payment_method": "card",
            "payment_reference": "PAY-SE1027",
            "order_date": date(2026, 10, 20),
            "shipping_date": None,
            "delivery_date": None,
        },
    ]
    statuses = ("pending", "processing", "shipped", "delivered", "cancelled")
    for number in range(1, 58):
        order_number = f"SE{1100 + number}"
        rows.append(
            {
                "id": stable_id(f"order-{order_number}"),
                "order_number": order_number,
                "customer_id": customer_by_number[((number - 1) % 20) + 1],
                "product": f"ShopEase product {number:02d}",
                "category": "home" if number % 2 else "electronics",
                "quantity": 1 if number % 4 else 2,
                "total_amount": Decimal(f"{25 + number * 1.75:.2f}"),
                "currency": "USD",
                "order_status": statuses[number % len(statuses)],
                "payment_status": "paid" if number % 9 else "duplicate_review",
                "payment_method": "card" if number % 3 else "wallet",
                "payment_reference": f"PAY-{order_number}",
                "order_date": date(2026, 9, 1) + timedelta(days=number),
                "shipping_date": date(2026, 9, 3) + timedelta(days=number)
                if number % 5
                else None,
                "delivery_date": date(2026, 9, 7) + timedelta(days=number)
                if number % 3 == 0
                else None,
            }
        )
    return rows


def seed() -> None:
    if SessionLocal is None:
        raise RuntimeError(
            "DATABASE_URL is required. Configure backend/.env before seeding."
        )

    customers = customer_rows()
    orders = order_rows(customers)
    with SessionLocal.begin() as session:
        existing_customer_ids = set(
            session.scalars(
                select(Customer.id).where(
                    Customer.id.in_(row["id"] for row in customers)
                )
            )
        )
        for row in customers:
            if row["id"] not in existing_customer_ids:
                session.add(Customer(**row))

        existing_order_numbers = set(
            session.scalars(
                select(Order.order_number).where(
                    Order.order_number.in_(row["order_number"] for row in orders)
                )
            )
        )
        for row in orders:
            if row["order_number"] not in existing_order_numbers:
                session.add(Order(**row))


if __name__ == "__main__":
    seed()
