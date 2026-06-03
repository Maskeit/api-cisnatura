"""protocol_product_id_optional

Revision ID: a1b2c3d4e5f6
Revises: d5f25d66e2a1
Create Date: 2026-06-02 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'd5f25d66e2a1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Eliminar el índice único en product_id (un protocolo ya no requiere producto principal)
    op.drop_index('ix_protocols_product_id', table_name='protocols')

    # Hacer la columna nullable
    op.alter_column('protocols', 'product_id', nullable=True)

    # Recrear el índice sin restricción de unicidad (útil para FK lookups)
    op.create_index(op.f('ix_protocols_product_id'), 'protocols', ['product_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_protocols_product_id'), table_name='protocols')
    op.alter_column('protocols', 'product_id', nullable=False)
    op.create_index('ix_protocols_product_id', 'protocols', ['product_id'], unique=True)
