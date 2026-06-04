"""Create dead_letter_events table for failed Kafka messages.

Revision ID: d4e8f1a92b03
Revises: beee9ff93ee7
Create Date: 2026-06-02

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d4e8f1a92b03"
down_revision: Union[str, Sequence[str], None] = "beee9ff93ee7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Store malformed or failed messages so we can inspect and replay them later."""
    op.create_table(
        "dead_letter_events",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("source_topic", sa.Text(), nullable=False),
        sa.Column("source_partition", sa.Integer(), nullable=False),
        sa.Column("source_offset", sa.BigInteger(), nullable=False),
        sa.Column("consumer_group", sa.Text(), nullable=False),
        sa.Column("error_type", sa.Text(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=False),
        sa.Column("payload", sa.Text(), nullable=True),
        sa.Column(
            "failed_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "resolved",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
    )

    op.create_index(
        "idx_dlq_source",
        "dead_letter_events",
        ["source_topic", "source_partition", "source_offset"],
    )
    op.create_index("idx_dlq_failed_at", "dead_letter_events", ["failed_at"])
    op.create_index("idx_dlq_resolved", "dead_letter_events", ["resolved"])


def downgrade() -> None:
    op.drop_index("idx_dlq_resolved", table_name="dead_letter_events")
    op.drop_index("idx_dlq_failed_at", table_name="dead_letter_events")
    op.drop_index("idx_dlq_source", table_name="dead_letter_events")
    op.drop_table("dead_letter_events")
