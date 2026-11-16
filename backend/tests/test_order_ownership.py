import uuid
from unittest.mock import Mock

from sqlalchemy.dialects import postgresql

from backend.app.services.order_service import get_customer_order


def test_order_lookup_requires_customer_and_order_identifiers() -> None:
    session = Mock()
    customer_id = uuid.uuid4()

    get_customer_order(session, customer_id, "SE1025")

    statement = session.scalar.call_args.args[0]
    compiled = str(
        statement.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": False},
        )
    )

    assert "orders.customer_id" in compiled
    assert "orders.order_number" in compiled
