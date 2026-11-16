import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.order import Order


def get_customer_order(
    session: Session, customer_id: uuid.UUID, order_number: str
) -> Order | None:
    """Return an order only when it belongs to the selected customer."""
    statement = select(Order).where(
        Order.customer_id == customer_id,
        Order.order_number == order_number,
    )
    return session.scalar(statement)
