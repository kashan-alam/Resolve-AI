import uuid

from sqlalchemy.orm import Session

from backend.app.services.order_service import get_customer_order
from backend.app.tools.registry import ToolDefinition, ToolRegistry
from backend.app.tools.schemas import OrderLookupArguments, ToolResult


def create_order_tool_registry(
    session: Session, customer_id: uuid.UUID
) -> ToolRegistry:
    registry = ToolRegistry()

    def lookup_order(arguments: OrderLookupArguments) -> ToolResult:
        order = get_customer_order(session, customer_id, arguments.order_number)
        if order is None:
            return ToolResult(
                data={"found": False, "order_number": arguments.order_number}
            )
        return ToolResult(
            data={
                "found": True,
                "order_number": order.order_number,
                "product": order.product,
                "category": order.category,
                "quantity": order.quantity,
                "total_amount": str(order.total_amount),
                "currency": order.currency,
                "order_status": order.order_status,
                "payment_status": order.payment_status,
                "order_date": order.order_date.isoformat(),
                "shipping_date": (
                    order.shipping_date.isoformat()
                    if order.shipping_date
                    else None
                ),
                "delivery_date": (
                    order.delivery_date.isoformat()
                    if order.delivery_date
                    else None
                ),
            }
        )

    registry.register(
        ToolDefinition(
            name="lookup_customer_order",
            description="Look up one order belonging to the selected demo customer.",
            arguments_model=OrderLookupArguments,
            handler=lookup_order,
        )
    )
    return registry
