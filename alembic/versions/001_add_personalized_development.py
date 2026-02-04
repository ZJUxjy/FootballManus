"""add personalized development fields

Revision ID: add_personalized_development
Revises:
Create Date: 2024-02-04

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = 'add_personalized_development'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Add development_type column
    op.add_column('players', sa.Column(
        'development_type', 
        sa.String(50), 
        server_default='standard',
        nullable=False
    ))
    
    # Add player_sub_type column
    op.add_column('players', sa.Column(
        'player_sub_type', 
        sa.String(50), 
        nullable=True
    ))
    
    # Add personality traits
    op.add_column('players', sa.Column(
        'professionalism', 
        sa.Integer, 
        server_default='10',
        nullable=False
    ))
    
    op.add_column('players', sa.Column(
        'ambition', 
        sa.Integer, 
        server_default='10',
        nullable=False
    ))
    
    op.add_column('players', sa.Column(
        'pressure_resistance', 
        sa.Integer, 
        server_default='10',
        nullable=False
    ))
    
    # Add growth curve parameters
    op.add_column('players', sa.Column(
        'peak_age_start', 
        sa.Integer, 
        server_default='24',
        nullable=False
    ))
    
    op.add_column('players', sa.Column(
        'peak_age_end', 
        sa.Integer, 
        server_default='28',
        nullable=False
    ))
    
    op.add_column('players', sa.Column(
        'growth_rate', 
        sa.Float, 
        server_default='1.0',
        nullable=False
    ))
    
    op.add_column('players', sa.Column(
        'decline_rate', 
        sa.Float, 
        server_default='1.0',
        nullable=False
    ))
    
    # Add environment factors
    op.add_column('players', sa.Column(
        'league_fit', 
        sa.Integer, 
        server_default='70',
        nullable=False
    ))
    
    # Add tracking fields
    op.add_column('players', sa.Column(
        'total_hours_trained', 
        sa.Integer, 
        server_default='0',
        nullable=False
    ))
    
    op.add_column('players', sa.Column(
        'coaches_mentored', 
        sa.Integer, 
        server_default='0',
        nullable=False
    ))


def downgrade():
    op.drop_column('players', 'coaches_mentored')
    op.drop_column('players', 'total_hours_trained')
    op.drop_column('players', 'league_fit')
    op.drop_column('players', 'decline_rate')
    op.drop_column('players', 'growth_rate')
    op.drop_column('players', 'peak_age_end')
    op.drop_column('players', 'peak_age_start')
    op.drop_column('players', 'pressure_resistance')
    op.drop_column('players', 'decline_rate')
    op.drop_column('players', 'ambition')
    op.drop_column('players', 'professionalism')
    op.drop_column('players', 'player_sub_type')
    op.drop_column('players', 'development_type')
