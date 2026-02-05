"""Initial migration with all models

Revision ID: 542edfe7b252
Revises: 
Create Date: 2026-02-03 12:31:41.432343

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '542edfe7b252'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('email', sa.String(255), unique=True, nullable=False, index=True),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=True),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('is_superuser', sa.Boolean, default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Create clusters table
    op.create_table(
        'clusters',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('type', sa.String(50), nullable=False),
        sa.Column('config', sa.JSON, nullable=False),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Create deployments table
    op.create_table(
        'deployments',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('cluster_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('compose_content', sa.Text, nullable=False),
        sa.Column('manifests', sa.JSON, nullable=False),
        sa.Column('status', sa.String(50), nullable=False, index=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('deployed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.ForeignKeyConstraint(['cluster_id'], ['clusters.id']),
    )

    # Create llm_configurations table
    op.create_table(
        'llm_configurations',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('provider', sa.String(50), nullable=False),
        sa.Column('api_key_encrypted', sa.LargeBinary, nullable=False),
        sa.Column('endpoint', sa.String(255), nullable=True),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Create alert_configurations table
    op.create_table(
        'alert_configurations',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('deployment_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('condition_type', sa.String(50), nullable=False),
        sa.Column('threshold_value', sa.Float, nullable=True),
        sa.Column('notification_channel', sa.String(50), nullable=False),
        sa.Column('notification_config', sa.JSON, nullable=False),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['deployment_id'], ['deployments.id']),
    )

    # Create templates table
    op.create_table(
        'templates',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('category', sa.String(100), nullable=True, index=True),
        sa.Column('compose_content', sa.Text, nullable=False),
        sa.Column('required_params', sa.JSON, nullable=True),
        sa.Column('is_public', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Create task_status table
    op.create_table(
        'task_status',
        sa.Column('id', sa.String(255), primary_key=True),
        sa.Column('user_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('task_type', sa.String(50), nullable=False),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('progress', sa.Integer, default=0),
        sa.Column('result', sa.JSON, nullable=True),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Create indexes
    op.create_index('idx_deployments_user_id', 'deployments', ['user_id'])
    op.create_index('idx_deployments_status', 'deployments', ['status'])
    op.create_index('idx_clusters_user_id', 'clusters', ['user_id'])
    op.create_index('idx_llm_configs_user_id', 'llm_configurations', ['user_id'])
    op.create_index('idx_alerts_deployment_id', 'alert_configurations', ['deployment_id'])
    op.create_index('idx_templates_category', 'templates', ['category'])


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes
    op.drop_index('idx_templates_category')
    op.drop_index('idx_alerts_deployment_id')
    op.drop_index('idx_llm_configs_user_id')
    op.drop_index('idx_clusters_user_id')
    op.drop_index('idx_deployments_status')
    op.drop_index('idx_deployments_user_id')
    
    # Drop tables in reverse order (respecting foreign key constraints)
    op.drop_table('task_status')
    op.drop_table('templates')
    op.drop_table('alert_configurations')
    op.drop_table('llm_configurations')
    op.drop_table('deployments')
    op.drop_table('clusters')
    op.drop_table('users')
