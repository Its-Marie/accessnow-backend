"""needs jsonb (manual)

Revision ID: eb9e3a8c706e
Revises: d4e05be2d79d
Create Date: 2026-02-24 11:43:41.209675

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'eb9e3a8c706e'
down_revision = 'd4e05be2d79d'
branch_labels = None
depends_on = None

def upgrade():
    op.execute('ALTER TABLE "user" ALTER COLUMN needs TYPE jsonb USING NULL;')

def downgrade():
    op.execute('ALTER TABLE "user" ALTER COLUMN needs TYPE text USING needs::text;')
