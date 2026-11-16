import uuid

from sqlalchemy import String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, TimestampMixin, uuid_column


class Customer(TimestampMixin, Base):
    __tablename__ = "customers"
    __table_args__ = (UniqueConstraint("email", name="uq_customers_email"),)

    id: Mapped[uuid.UUID] = uuid_column()
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False)

    orders = relationship("Order", back_populates="customer")
    conversations = relationship("Conversation", back_populates="customer")
    tickets = relationship("Ticket", back_populates="customer")
