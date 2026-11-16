"""Create the Phase 2 relational schema.

Revision ID: 0001_initial_relational_schema
Revises:
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0001_initial_relational_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "customers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("email", name="uq_customers_email"),
    )
    op.create_table(
        "orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("order_number", sa.String(32), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product", sa.String(200), nullable=False),
        sa.Column("category", sa.String(80), nullable=False),
        sa.Column("quantity", sa.Integer, nullable=False),
        sa.Column("total_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("order_status", sa.String(32), nullable=False),
        sa.Column("payment_status", sa.String(32), nullable=False),
        sa.Column("payment_method", sa.String(32), nullable=False),
        sa.Column("payment_reference", sa.String(80), nullable=False),
        sa.Column("order_date", sa.Date, nullable=False),
        sa.Column("shipping_date", sa.Date),
        sa.Column("delivery_date", sa.Date),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("order_number", name="uq_orders_order_number"),
    )
    op.create_table(
        "conversations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="RESTRICT"),
    )
    op.create_table(
        "messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sender_type", sa.String(32), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="RESTRICT"),
    )
    op.create_table(
        "tickets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("ticket_number", sa.String(32), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_id", postgresql.UUID(as_uuid=True)),
        sa.Column("category", sa.String(32), nullable=False),
        sa.Column("issue_type", sa.String(32), nullable=False),
        sa.Column("issue_key", sa.String(64), nullable=False),
        sa.Column("priority", sa.String(16), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("escalation_reason", sa.Text),
        sa.Column("assigned_team", sa.String(32)),
        sa.Column("ai_summary", sa.Text),
        sa.Column("extracted_information", postgresql.JSONB),
        sa.Column("ai_suggested_resolution", sa.Text),
        sa.Column("ai_draft_response", sa.Text),
        sa.Column("final_response", sa.Text),
        sa.Column("requires_human_review", sa.Boolean, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("closed_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("ticket_number", name="uq_tickets_ticket_number"),
    )
    op.create_table(
        "ticket_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("ticket_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("old_value", sa.Text),
        sa.Column("new_value", sa.Text),
        sa.Column("internal_note", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"], ondelete="RESTRICT"),
    )
    op.create_table(
        "knowledge_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("document_key", sa.String(100), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("category", sa.String(80), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("embedding_model", sa.String(120)),
        sa.Column("embedding_dimension", sa.Integer),
        sa.Column("embedding_configuration", postgresql.JSONB),
        sa.Column("is_active", sa.Boolean, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("document_key", "version", name="uq_knowledge_documents_key_version"),
    )
    op.create_table(
        "document_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chunk_index", sa.Integer, nullable=False),
        sa.Column("chunk_text", sa.Text, nullable=False),
        sa.Column("metadata", postgresql.JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["knowledge_documents.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("document_id", "chunk_index", name="uq_document_chunks_document_index"),
    )
    op.create_table(
        "ticket_policy_evidence",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("ticket_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True)),
        sa.Column("chunk_id", postgresql.UUID(as_uuid=True)),
        sa.Column("document_title", sa.String(200), nullable=False),
        sa.Column("chunk_text", sa.Text, nullable=False),
        sa.Column("similarity_score", sa.Numeric(8, 6)),
        sa.Column("evidence_classification", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["document_id"], ["knowledge_documents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["chunk_id"], ["document_chunks.id"], ondelete="SET NULL"),
    )
    op.create_table(
        "knowledge_gaps",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("normalized_question", sa.String(500), nullable=False),
        sa.Column("example_question", sa.Text, nullable=False),
        sa.Column("category", sa.String(32), nullable=False),
        sa.Column("occurrence_count", sa.Integer, nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("approved_answer", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "knowledge_gap_tickets",
        sa.Column("knowledge_gap_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ticket_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["knowledge_gap_id"], ["knowledge_gaps.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("knowledge_gap_id", "ticket_id"),
    )

    for table, columns in {
        "orders": ["customer_id"],
        "conversations": ["customer_id"],
        "messages": ["conversation_id", "created_at"],
        "tickets": ["conversation_id", "customer_id", "order_id", "issue_key"],
        "ticket_events": ["ticket_id"],
        "document_chunks": ["document_id"],
        "ticket_policy_evidence": ["ticket_id", "document_id", "chunk_id"],
        "knowledge_gaps": ["normalized_question"],
    }.items():
        for column in columns:
            op.create_index(f"ix_{table}_{column}", table, [column])

    op.create_index(
        "uq_knowledge_documents_active_key",
        "knowledge_documents",
        ["document_key"],
        unique=True,
        postgresql_where=sa.text("is_active = true"),
    )
    op.create_index(
        "uq_tickets_active_issue_key",
        "tickets",
        ["issue_key"],
        unique=True,
        postgresql_where=sa.text(
            "status IN ('open', 'pending_human_review', 'assigned', 'in_progress')"
        ),
    )


def downgrade() -> None:
    op.drop_table("knowledge_gap_tickets")
    op.drop_table("knowledge_gaps")
    op.drop_table("ticket_policy_evidence")
    op.drop_table("document_chunks")
    op.drop_table("knowledge_documents")
    op.drop_table("ticket_events")
    op.drop_table("tickets")
    op.drop_table("messages")
    op.drop_table("conversations")
    op.drop_table("orders")
    op.drop_table("customers")
    # The extension may predate this migration or be used by other objects.
    # Leave it enabled during downgrade.
