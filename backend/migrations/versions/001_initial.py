"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-04-06

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('username', sa.String(255), unique=True, nullable=False),
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('last_active_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    )

    # Create projects table
    op.create_table(
        'projects',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('path', sa.String(1024), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('last_analyzed_at', sa.DateTime(), nullable=True),
    )
    op.create_index('idx_projects_user_path', 'projects', ['user_id', 'path'], unique=True)

    # Create sessions table
    op.create_table(
        'sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('last_active_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('metadata', postgresql.JSON(), nullable=True),
    )
    op.create_index('idx_sessions_project_id', 'sessions', ['project_id'])

    # Create interactions table
    op.create_table(
        'interactions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_message', sa.Text(), nullable=False),
        sa.Column('ai_response', sa.Text(), nullable=False),
        sa.Column('interaction_type', sa.String(50), server_default='query', nullable=False),
        sa.Column('sources', postgresql.JSON(), server_default='[]', nullable=False),
        sa.Column('files_analyzed', sa.Integer(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    )
    op.create_index('idx_interactions_session_id', 'interactions', ['session_id'])
    op.create_index('idx_interactions_created_at', 'interactions', ['created_at'])

    # Create code_explanations table
    op.create_table(
        'code_explanations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('file_path', sa.String(1024), nullable=False),
        sa.Column('code_hash', sa.String(64), nullable=False),
        sa.Column('explanation', sa.Text(), nullable=False),
        sa.Column('language', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    )
    op.create_index('idx_code_explanations_project_hash', 'code_explanations', ['project_id', 'code_hash'], unique=True)

    # Create issues table
    op.create_table(
        'issues',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('sessions.id', ondelete='SET NULL'), nullable=True),
        sa.Column('file_path', sa.String(1024), nullable=False),
        sa.Column('line_start', sa.Integer(), nullable=True),
        sa.Column('line_end', sa.Integer(), nullable=True),
        sa.Column('severity', sa.String(20), nullable=False),
        sa.Column('category', sa.String(50), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('suggested_fix', sa.Text(), nullable=True),
        sa.Column('detected_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    )
    op.create_index('idx_issues_project_id', 'issues', ['project_id'])
    op.create_index('idx_issues_severity', 'issues', ['severity'])

    # Create quiz_sessions table
    op.create_table(
        'quiz_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('current_question_index', sa.Integer(), server_default='0', nullable=False),
        sa.Column('total_questions', sa.Integer(), server_default='0', nullable=False),
        sa.Column('correct_answers', sa.Integer(), server_default='0', nullable=False),
        sa.Column('status', sa.String(20), server_default='active', nullable=False),
        sa.Column('started_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
    )
    op.create_index('idx_quiz_sessions_session_id', 'quiz_sessions', ['session_id'])

    # Create quiz_questions table
    op.create_table(
        'quiz_questions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('quiz_session_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('quiz_sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('question_text', sa.Text(), nullable=False),
        sa.Column('question_type', sa.String(50), nullable=False),
        sa.Column('code_context', sa.Text(), nullable=True),
        sa.Column('options', postgresql.JSON(), server_default='[]', nullable=False),
        sa.Column('correct_answer', sa.String(255), nullable=False),
        sa.Column('explanation', sa.Text(), nullable=True),
        sa.Column('file_source', sa.String(1024), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    )

    # Create quiz_answers table
    op.create_table(
        'quiz_answers',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('question_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('quiz_questions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('selected_answer', sa.String(255), nullable=True),
        sa.Column('is_correct', sa.Boolean(), nullable=False),
        sa.Column('answered_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('quiz_answers')
    op.drop_table('quiz_questions')
    op.drop_table('quiz_sessions')
    op.drop_index('idx_issues_severity', table_name='issues')
    op.drop_index('idx_issues_project_id', table_name='issues')
    op.drop_table('issues')
    op.drop_index('idx_code_explanations_project_hash', table_name='code_explanations')
    op.drop_table('code_explanations')
    op.drop_index('idx_interactions_created_at', table_name='interactions')
    op.drop_index('idx_interactions_session_id', table_name='interactions')
    op.drop_table('interactions')
    op.drop_index('idx_sessions_project_id', table_name='sessions')
    op.drop_table('sessions')
    op.drop_index('idx_projects_user_path', table_name='projects')
    op.drop_table('projects')
    op.drop_table('users')
