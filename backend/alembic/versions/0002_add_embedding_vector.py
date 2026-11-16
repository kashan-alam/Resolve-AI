"""Add verified 768-dimensional document embeddings.

Revision ID: 0002_add_embedding_vector
Revises: 0001_initial_relational_schema
"""

from alembic import op
from pgvector.sqlalchemy import Vector
import sqlalchemy as sa


revision = "0002_add_embedding_vector"
down_revision = "0001_initial_relational_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "document_chunks",
        sa.Column("embedding", Vector(768), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("document_chunks", "embedding")
