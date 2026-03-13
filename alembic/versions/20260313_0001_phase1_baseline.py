"""phase1 baseline

Revision ID: 20260313_0001
Revises:
Create Date: 2026-03-13 12:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260313_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "companies_v2",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("external_key", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("industry", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("region", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("country", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("priority", sa.String(length=8), nullable=False, server_default=""),
        sa.Column("ats", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("career_url", sa.Text(), nullable=False),
        sa.Column("international_hiring", sa.String(length=60), nullable=False, server_default=""),
        sa.Column("profile_fit", sa.String(length=60), nullable=False, server_default=""),
        sa.Column("salary_band", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_companies_v2_external_key", "companies_v2", ["external_key"], unique=True)
    op.create_index("ix_companies_v2_name", "companies_v2", ["name"], unique=False)

    op.create_table(
        "users_v2",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("password_hash", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("locale", sa.String(length=16), nullable=False, server_default="es-MX"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_users_v2_email", "users_v2", ["email"], unique=True)

    op.create_table(
        "user_profiles_v2",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users_v2.id", ondelete="CASCADE"), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False, server_default="Default"),
        sa.Column("target_role", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("practice_area", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("seniority_target", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("preferred_regions", sa.Text(), nullable=False, server_default=""),
        sa.Column("preferred_countries", sa.Text(), nullable=False, server_default=""),
        sa.Column("preferred_work_modes", sa.Text(), nullable=False, server_default=""),
        sa.Column("preferred_companies", sa.Text(), nullable=False, server_default=""),
        sa.Column("keywords", sa.Text(), nullable=False, server_default=""),
        sa.Column("years_experience", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_user_profiles_v2_user_id", "user_profiles_v2", ["user_id"], unique=False)

    op.create_table(
        "skills_v2",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("normalized_name", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_skills_v2_name", "skills_v2", ["name"], unique=True)
    op.create_index("ix_skills_v2_normalized_name", "skills_v2", ["normalized_name"], unique=True)

    op.create_table(
        "jobs_v2",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("canonical_key", sa.String(length=500), nullable=False),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies_v2.id", ondelete="SET NULL"), nullable=True),
        sa.Column("source_job_id", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("source_url", sa.Text(), nullable=False, server_default=""),
        sa.Column("apply_url", sa.Text(), nullable=False, server_default=""),
        sa.Column("ats", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("normalized_title", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("location_text", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("country", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("region", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("work_mode", sa.String(length=40), nullable=False, server_default=""),
        sa.Column("department", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("seniority_level", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("employment_type", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("posted_date_raw", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("description_raw", sa.Text(), nullable=False, server_default=""),
        sa.Column("description_snippet", sa.Text(), nullable=False, server_default=""),
        sa.Column("priority", sa.String(length=8), nullable=False, server_default=""),
        sa.Column("global_signal", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("canonical_key", name="jobs_v2_canonical_key_uq"),
    )
    op.create_index("ix_jobs_v2_canonical_key", "jobs_v2", ["canonical_key"], unique=False)
    op.create_index("ix_jobs_v2_title", "jobs_v2", ["title"], unique=False)
    op.create_index("ix_jobs_v2_normalized_title", "jobs_v2", ["normalized_title"], unique=False)
    op.create_index("ix_jobs_v2_country", "jobs_v2", ["country"], unique=False)
    op.create_index("ix_jobs_v2_region", "jobs_v2", ["region"], unique=False)
    op.create_index("ix_jobs_v2_seniority_level", "jobs_v2", ["seniority_level"], unique=False)

    op.create_table(
        "job_skills_v2",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("job_id", sa.Integer(), sa.ForeignKey("jobs_v2.id", ondelete="CASCADE"), nullable=False),
        sa.Column("skill_id", sa.Integer(), sa.ForeignKey("skills_v2.id", ondelete="CASCADE"), nullable=False),
        sa.Column("evidence_text", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1"),
        sa.UniqueConstraint("job_id", "skill_id", name="job_skills_v2_job_skill_uq"),
    )
    op.create_index("ix_job_skills_v2_job_id", "job_skills_v2", ["job_id"], unique=False)
    op.create_index("ix_job_skills_v2_skill_id", "job_skills_v2", ["skill_id"], unique=False)

    op.create_table(
        "user_skills_v2",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_profile_id", sa.Integer(), sa.ForeignKey("user_profiles_v2.id", ondelete="CASCADE"), nullable=False),
        sa.Column("skill_id", sa.Integer(), sa.ForeignKey("skills_v2.id", ondelete="CASCADE"), nullable=False),
        sa.Column("years_experience", sa.Float(), nullable=False, server_default="0"),
        sa.Column("evidence_text", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1"),
        sa.UniqueConstraint("user_profile_id", "skill_id", name="user_skills_v2_profile_skill_uq"),
    )
    op.create_index("ix_user_skills_v2_user_profile_id", "user_skills_v2", ["user_profile_id"], unique=False)
    op.create_index("ix_user_skills_v2_skill_id", "user_skills_v2", ["skill_id"], unique=False)

    op.create_table(
        "ingestion_runs_v2",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("run_type", sa.String(length=40), nullable=False, server_default="manual"),
        sa.Column("profile_name", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="completed"),
        sa.Column("persisted_companies", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("persisted_jobs", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("persisted_job_skills", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("persisted_user_skills", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("recalculated_matches", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "job_matches_v2",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("job_id", sa.Integer(), sa.ForeignKey("jobs_v2.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_profile_id", sa.Integer(), sa.ForeignKey("user_profiles_v2.id", ondelete="CASCADE"), nullable=False),
        sa.Column("total_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("score_band", sa.String(length=40), nullable=False, server_default="low"),
        sa.Column("keyword_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("seniority_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("geography_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("work_mode_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("company_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("explanation", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_job_matches_v2_job_id", "job_matches_v2", ["job_id"], unique=False)
    op.create_index("ix_job_matches_v2_user_profile_id", "job_matches_v2", ["user_profile_id"], unique=False)

    op.create_table(
        "resumes_v2",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users_v2.id", ondelete="CASCADE"), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("content_hash", sa.String(length=128), nullable=False),
        sa.Column("extracted_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("parser_version", sa.String(length=80), nullable=False, server_default="v1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_resumes_v2_user_id", "resumes_v2", ["user_id"], unique=False)
    op.create_index("ix_resumes_v2_content_hash", "resumes_v2", ["content_hash"], unique=False)

    op.create_table(
        "resume_evidence_v2",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("resume_id", sa.Integer(), sa.ForeignKey("resumes_v2.id", ondelete="CASCADE"), nullable=False),
        sa.Column("evidence_type", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("evidence_value", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("evidence_text", sa.Text(), nullable=False, server_default=""),
    )
    op.create_index("ix_resume_evidence_v2_resume_id", "resume_evidence_v2", ["resume_id"], unique=False)

    op.create_table(
        "applications_v2",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users_v2.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_profile_id", sa.Integer(), sa.ForeignKey("user_profiles_v2.id", ondelete="SET NULL"), nullable=True),
        sa.Column("job_id", sa.Integer(), sa.ForeignKey("jobs_v2.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(length=80), nullable=False, server_default="saved"),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_applications_v2_user_id", "applications_v2", ["user_id"], unique=False)
    op.create_index("ix_applications_v2_job_id", "applications_v2", ["job_id"], unique=False)
    op.create_index("ix_applications_v2_status", "applications_v2", ["status"], unique=False)

    op.create_table(
        "application_reminders_v2",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("application_id", sa.Integer(), sa.ForeignKey("applications_v2.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reminder_type", sa.String(length=80), nullable=False, server_default="follow_up"),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="pending"),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
    )
    op.create_index("ix_application_reminders_v2_application_id", "application_reminders_v2", ["application_id"], unique=False)

    op.create_table(
        "alerts_v2",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users_v2.id", ondelete="CASCADE"), nullable=False),
        sa.Column("channel", sa.String(length=40), nullable=False, server_default="email"),
        sa.Column("minimum_score", sa.Integer(), nullable=False, server_default="70"),
        sa.Column("cadence", sa.String(length=40), nullable=False, server_default="daily"),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_alerts_v2_user_id", "alerts_v2", ["user_id"], unique=False)

    op.create_table(
        "events_v2",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users_v2.id", ondelete="SET NULL"), nullable=True),
        sa.Column("event_type", sa.String(length=120), nullable=False),
        sa.Column("entity_type", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("entity_id", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("payload_json", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_events_v2_user_id", "events_v2", ["user_id"], unique=False)
    op.create_index("ix_events_v2_event_type", "events_v2", ["event_type"], unique=False)


def downgrade() -> None:
    for index_name, table_name in [
        ("ix_events_v2_event_type", "events_v2"),
        ("ix_events_v2_user_id", "events_v2"),
        ("ix_alerts_v2_user_id", "alerts_v2"),
        ("ix_application_reminders_v2_application_id", "application_reminders_v2"),
        ("ix_applications_v2_status", "applications_v2"),
        ("ix_applications_v2_job_id", "applications_v2"),
        ("ix_applications_v2_user_id", "applications_v2"),
        ("ix_resume_evidence_v2_resume_id", "resume_evidence_v2"),
        ("ix_resumes_v2_content_hash", "resumes_v2"),
        ("ix_resumes_v2_user_id", "resumes_v2"),
        ("ix_job_matches_v2_user_profile_id", "job_matches_v2"),
        ("ix_job_matches_v2_job_id", "job_matches_v2"),
        ("ix_user_skills_v2_skill_id", "user_skills_v2"),
        ("ix_user_skills_v2_user_profile_id", "user_skills_v2"),
        ("ix_job_skills_v2_skill_id", "job_skills_v2"),
        ("ix_job_skills_v2_job_id", "job_skills_v2"),
        ("ix_jobs_v2_seniority_level", "jobs_v2"),
        ("ix_jobs_v2_region", "jobs_v2"),
        ("ix_jobs_v2_country", "jobs_v2"),
        ("ix_jobs_v2_normalized_title", "jobs_v2"),
        ("ix_jobs_v2_title", "jobs_v2"),
        ("ix_jobs_v2_canonical_key", "jobs_v2"),
        ("ix_skills_v2_normalized_name", "skills_v2"),
        ("ix_skills_v2_name", "skills_v2"),
        ("ix_user_profiles_v2_user_id", "user_profiles_v2"),
        ("ix_users_v2_email", "users_v2"),
        ("ix_companies_v2_name", "companies_v2"),
        ("ix_companies_v2_external_key", "companies_v2"),
    ]:
        op.drop_index(index_name, table_name=table_name)

    for table_name in [
        "events_v2",
        "alerts_v2",
        "application_reminders_v2",
        "applications_v2",
        "resume_evidence_v2",
        "resumes_v2",
        "job_matches_v2",
        "ingestion_runs_v2",
        "user_skills_v2",
        "job_skills_v2",
        "jobs_v2",
        "skills_v2",
        "user_profiles_v2",
        "users_v2",
        "companies_v2",
    ]:
        op.drop_table(table_name)
