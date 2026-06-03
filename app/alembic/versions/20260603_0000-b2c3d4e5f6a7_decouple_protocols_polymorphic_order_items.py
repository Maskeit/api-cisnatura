"""decouple protocols from products + polymorphic order items

Desacopla los protocolos de los productos:
- order_items pasa a ser polimórfico: puede referenciar un producto O un protocolo
  (item_type + product_id nullable + protocol_id).
- protocols pierde product_id (el puente de "producto digital" desaparece). La única
  relación protocolo↔producto que queda es la recomendación (tabla protocol_products).

NOTA: los productos digitales históricos creados como puente NO se eliminan; las órdenes
y accesos antiguos siguen siendo válidos (item_type queda en 'product' por defecto).

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-06-03 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ---- order_items: polimórfico (producto o protocolo) ----
    op.add_column(
        'order_items',
        sa.Column('item_type', sa.String(length=20), nullable=False, server_default='product')
    )
    op.create_index(op.f('ix_order_items_item_type'), 'order_items', ['item_type'], unique=False)

    op.add_column('order_items', sa.Column('protocol_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_order_items_protocol_id'), 'order_items', ['protocol_id'], unique=False)
    op.create_foreign_key(
        'fk_order_items_protocol_id_protocols',
        'order_items', 'protocols',
        ['protocol_id'], ['id']
    )

    # product_id ahora es opcional (los items de protocolo no tienen producto)
    op.alter_column('order_items', 'product_id', existing_type=sa.Integer(), nullable=True)

    # ---- protocols: eliminar el puente con products ----
    op.drop_index('ix_protocols_product_id', table_name='protocols')
    op.drop_column('protocols', 'product_id')  # Postgres elimina la FK asociada automáticamente


def downgrade() -> None:
    # ---- protocols: restaurar product_id ----
    op.add_column('protocols', sa.Column('product_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'protocols_product_id_fkey',
        'protocols', 'products',
        ['product_id'], ['id']
    )
    op.create_index('ix_protocols_product_id', 'protocols', ['product_id'], unique=False)

    # ---- order_items: revertir a solo-producto ----
    op.drop_constraint('fk_order_items_protocol_id_protocols', 'order_items', type_='foreignkey')
    op.drop_index(op.f('ix_order_items_protocol_id'), table_name='order_items')
    op.drop_column('order_items', 'protocol_id')

    op.drop_index(op.f('ix_order_items_item_type'), table_name='order_items')
    op.drop_column('order_items', 'item_type')

    # Atención: filas de protocolo dejan product_id NULL; esto puede fallar si existen.
    op.alter_column('order_items', 'product_id', existing_type=sa.Integer(), nullable=False)
