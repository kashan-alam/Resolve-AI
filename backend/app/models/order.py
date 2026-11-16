import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, TimestampMixin, uuid_column


class Order(TimestampMixin, Base):
    __tablename__ = "orders"
    __table_args__ = (
        UniqueConstraint("order_number", name="uq_orders_order_number"),
    )

    id: Mapped[uuid.UUID] = uuid_column()
    order_number: Mapped[str] = mapped_column(String(32), nullable=False)
    customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    product: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(80), nullable=False)
    quantity: Mapped[int] = mapped_column(nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    order_status: Mapped[str] = mapped_column(String(32), nullable=False)
    payment_status: Mapped[str] = mapped_column(String(32), nullable=False)
    payment_method: Mapped[str] = mapped_column(String(32), nullable=False)
    payment_reference: Mapped[str] = mapped_column(String(80), nullable=False)
    order_date: Mapped[date] = mapped_column(Date, nullable=False)
    shipping_date: Mapped[date | None] = mapped_column(Date)
    delivery_date: Mapped[date | None] = mapped_column(Date)

    customer = relationship("Customer", back_populates="orders")
    tickets = relationship("Ticket", back_populates="order")
