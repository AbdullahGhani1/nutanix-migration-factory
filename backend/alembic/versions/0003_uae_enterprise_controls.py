"""Add data residency, DR objective and site metadata.

Revision ID: 0003_uae_enterprise_controls
Revises: 0002_migration_execution
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0003_uae_enterprise_controls"
down_revision: Union[str, None] = "0002_migration_execution"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("workloads") as batch:
        batch.add_column(sa.Column("data_classification", sa.String(length=32), nullable=False, server_default="Internal"))
        batch.add_column(sa.Column("residency", sa.String(length=128), nullable=False, server_default=""))
        batch.add_column(sa.Column("rpo_minutes", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("rto_minutes", sa.Integer(), nullable=True))
    with op.batch_alter_table("target_clusters") as batch:
        batch.add_column(sa.Column("country_code", sa.String(length=2), nullable=False, server_default=""))
        batch.add_column(sa.Column("site_name", sa.String(length=128), nullable=False, server_default=""))


def downgrade() -> None:
    with op.batch_alter_table("target_clusters") as batch:
        batch.drop_column("site_name")
        batch.drop_column("country_code")
    with op.batch_alter_table("workloads") as batch:
        batch.drop_column("rto_minutes")
        batch.drop_column("rpo_minutes")
        batch.drop_column("residency")
        batch.drop_column("data_classification")
