"""add admin_settings table

Revision ID: 001_admin_settings
Revises: 
Create Date: 2025-11-30 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_admin_settings'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Crear tabla admin_settings para configuraciones administrativas.
    """
    op.create_table(
        'admin_settings',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('maintenance_mode', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('maintenance_message', sa.String(length=500), nullable=True, 
                  server_default='Sistema en mantenimiento. Intente más tarde.'),
        sa.Column('shipping_price', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('free_shipping_threshold', sa.Float(), nullable=True),
        sa.Column('global_discount_enabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('global_discount_percentage', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('global_discount_name', sa.String(length=100), nullable=True, 
                  server_default='Oferta Especial'),
        sa.Column('category_discounts', postgresql.JSON(astext_type=sa.Text()), nullable=False, 
                  server_default='{}'),
        sa.Column('product_discounts', postgresql.JSON(astext_type=sa.Text()), nullable=False, 
                  server_default='{}'),
        sa.Column('seasonal_offers', postgresql.JSON(astext_type=sa.Text()), nullable=False, 
                  server_default='[]'),
        sa.Column('allow_user_registration', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('max_items_per_order', sa.Integer(), nullable=False, server_default='50'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_admin_settings_id'), 'admin_settings', ['id'], unique=False)
    
    # Insertar registro inicial con valores por defecto
    op.execute("""
        INSERT INTO admin_settings (
            id,
            maintenance_mode,
            maintenance_message,
            shipping_price,
            free_shipping_threshold,
            global_discount_enabled,
            global_discount_percentage,
            global_discount_name,
            category_discounts,
            product_discounts,
            seasonal_offers,
            allow_user_registration,
            max_items_per_order,
            created_at,
            updated_at
        ) VALUES (
            gen_random_uuid(),
            false,
            'Sistema en mantenimiento. Intente más tarde.',
            0.0,
            NULL,
            false,
            0.0,
            'Oferta Especial',
            '{}',
            '{}',
            '[]',
            true,
            50,
            now(),
            now()
        )
    """)


def downgrade() -> None:
    """
    Eliminar tabla admin_settings.
    """
    op.drop_index(op.f('ix_admin_settings_id'), table_name='admin_settings')
    op.drop_table('admin_settings')
