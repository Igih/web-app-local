"""Create the isolated asset schema and core tables.

Revision ID: 0001
Revises:
Create Date: 2026-11-18
"""

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    statements = [
        "CREATE SCHEMA IF NOT EXISTS asset",
        """
        CREATE TABLE asset.categories (
            id SMALLSERIAL PRIMARY KEY,
            name VARCHAR(50) NOT NULL,
            display_name VARCHAR(100) NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_asset_categories_name UNIQUE (name)
        )
        """,
        """
        CREATE TABLE asset.import_batches (
            id BIGSERIAL PRIMARY KEY,
            batch_name VARCHAR(255),
            image_path TEXT NOT NULL,
            annotation_path TEXT,
            category_name VARCHAR(50) NOT NULL,
            capture_type VARCHAR(20),
            spectral_type VARCHAR(20),
            tags TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
            recursive BOOLEAN NOT NULL DEFAULT TRUE,
            status VARCHAR(32) NOT NULL DEFAULT 'created',
            scan_total INTEGER NOT NULL DEFAULT 0 CHECK (scan_total >= 0),
            scan_image_count INTEGER NOT NULL DEFAULT 0 CHECK (scan_image_count >= 0),
            scan_issue_count INTEGER NOT NULL DEFAULT 0 CHECK (scan_issue_count >= 0),
            import_total INTEGER NOT NULL DEFAULT 0 CHECK (import_total >= 0),
            import_imported INTEGER NOT NULL DEFAULT 0 CHECK (import_imported >= 0),
            import_duplicate INTEGER NOT NULL DEFAULT 0 CHECK (import_duplicate >= 0),
            import_failed INTEGER NOT NULL DEFAULT 0 CHECK (import_failed >= 0),
            error_message TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT ck_asset_import_batches_status CHECK (
                status IN (
                    'created',
                    'scanning',
                    'awaiting_confirmation',
                    'queued',
                    'importing',
                    'completed',
                    'partial',
                    'failed',
                    'stopped'
                )
            ),
            CONSTRAINT ck_asset_import_batches_capture_type CHECK (
                capture_type IS NULL OR capture_type IN ('photo', 'hand_drawn')
            ),
            CONSTRAINT ck_asset_import_batches_spectral_type CHECK (
                spectral_type IS NULL OR spectral_type IN ('visible', 'infrared')
            ),
            CONSTRAINT ck_asset_import_batches_type_consistency CHECK (
                capture_type IS NOT NULL OR spectral_type IS NULL
            )
        )
        """,
        """
        CREATE TABLE asset.tags (
            id SERIAL PRIMARY KEY,
            normalized_name VARCHAR(100) NOT NULL,
            display_name VARCHAR(100) NOT NULL,
            enabled BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_asset_tags_normalized_name UNIQUE (normalized_name)
        )
        """,
        """
        CREATE TABLE asset.images (
            id BIGSERIAL PRIMARY KEY,
            sha256 CHAR(64) NOT NULL,
            storage_key TEXT NOT NULL,
            category_id SMALLINT NOT NULL REFERENCES asset.categories(id) ON DELETE RESTRICT,
            capture_type VARCHAR(20),
            spectral_type VARCHAR(20),
            width INTEGER CHECK (width >= 0),
            height INTEGER CHECK (height >= 0),
            file_format VARCHAR(20),
            byte_size BIGINT CHECK (byte_size >= 0),
            status VARCHAR(32) NOT NULL DEFAULT 'pending',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_asset_images_sha256 UNIQUE (sha256),
            CONSTRAINT uq_asset_images_storage_key UNIQUE (storage_key),
            CONSTRAINT ck_asset_images_capture_type CHECK (
                capture_type IS NULL OR capture_type IN ('photo', 'hand_drawn')
            ),
            CONSTRAINT ck_asset_images_spectral_type CHECK (
                spectral_type IS NULL OR spectral_type IN ('visible', 'infrared')
            ),
            CONSTRAINT ck_asset_images_type_consistency CHECK (
                capture_type IS NOT NULL OR spectral_type IS NULL
            ),
            CONSTRAINT ck_asset_images_status CHECK (
                status IN ('pending', 'ready', 'quarantined', 'failed')
            )
        )
        """,
        """
        CREATE TABLE asset.image_sources (
            id BIGSERIAL PRIMARY KEY,
            image_id BIGINT NOT NULL REFERENCES asset.images(id) ON DELETE CASCADE,
            batch_id BIGINT NOT NULL REFERENCES asset.import_batches(id) ON DELETE CASCADE,
            source_path TEXT NOT NULL,
            source_filename TEXT NOT NULL,
            relative_path TEXT NOT NULL,
            normalized_relative_path TEXT NOT NULL,
            source_machine TEXT,
            declared_category_name VARCHAR(50) NOT NULL,
            declared_capture_type VARCHAR(20),
            declared_spectral_type VARCHAR(20),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_asset_image_sources_batch_relative UNIQUE (
                batch_id, normalized_relative_path
            ),
            CONSTRAINT ck_asset_image_sources_capture_type CHECK (
                declared_capture_type IS NULL OR declared_capture_type IN ('photo', 'hand_drawn')
            ),
            CONSTRAINT ck_asset_image_sources_spectral_type CHECK (
                declared_spectral_type IS NULL OR declared_spectral_type IN ('visible', 'infrared')
            ),
            CONSTRAINT ck_asset_image_sources_type_consistency CHECK (
                declared_capture_type IS NOT NULL OR declared_spectral_type IS NULL
            )
        )
        """,
        """
        CREATE TABLE asset.annotation_files (
            id BIGSERIAL PRIMARY KEY,
            batch_id BIGINT NOT NULL REFERENCES asset.import_batches(id) ON DELETE CASCADE,
            image_id BIGINT REFERENCES asset.images(id) ON DELETE SET NULL,
            storage_key TEXT NOT NULL,
            source_path TEXT NOT NULL,
            source_filename TEXT NOT NULL,
            relative_path TEXT NOT NULL,
            sha256 CHAR(64) NOT NULL,
            match_status VARCHAR(32) NOT NULL DEFAULT 'pending',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_asset_annotation_files_batch_relative UNIQUE (
                batch_id, relative_path
            ),
            CONSTRAINT ck_asset_annotation_files_match_status CHECK (
                match_status IN ('pending', 'matched', 'ambiguous', 'unmatched')
            )
        )
        """,
        """
        CREATE TABLE asset.image_tags (
            id BIGSERIAL PRIMARY KEY,
            image_id BIGINT NOT NULL REFERENCES asset.images(id) ON DELETE CASCADE,
            tag_id INTEGER NOT NULL REFERENCES asset.tags(id) ON DELETE CASCADE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_asset_image_tags_image_tag UNIQUE (image_id, tag_id)
        )
        """,
        """
        CREATE TABLE asset.import_items (
            id BIGSERIAL PRIMARY KEY,
            batch_id BIGINT NOT NULL REFERENCES asset.import_batches(id) ON DELETE CASCADE,
            image_id BIGINT REFERENCES asset.images(id) ON DELETE SET NULL,
            annotation_file_id BIGINT REFERENCES asset.annotation_files(id) ON DELETE SET NULL,
            source_path TEXT NOT NULL,
            normalized_relative_path TEXT NOT NULL,
            source_filename TEXT NOT NULL,
            source_machine TEXT,
            status VARCHAR(32) NOT NULL DEFAULT 'pending',
            sha256 CHAR(64),
            error_code VARCHAR(64),
            error_detail TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_asset_import_items_batch_relative UNIQUE (
                batch_id, normalized_relative_path
            ),
            CONSTRAINT ck_asset_import_items_status CHECK (
                status IN (
                    'pending',
                    'processing',
                    'imported',
                    'duplicate',
                    'conflict',
                    'failed',
                    'skipped'
                )
            )
        )
        """,
        """
        CREATE TABLE asset.import_issues (
            id BIGSERIAL PRIMARY KEY,
            batch_id BIGINT NOT NULL REFERENCES asset.import_batches(id) ON DELETE CASCADE,
            import_item_id BIGINT REFERENCES asset.import_items(id) ON DELETE CASCADE,
            image_id BIGINT REFERENCES asset.images(id) ON DELETE SET NULL,
            issue_type VARCHAR(64) NOT NULL,
            severity VARCHAR(16) NOT NULL DEFAULT 'warning',
            message TEXT NOT NULL,
            details JSONB NOT NULL DEFAULT '{}'::JSONB,
            status VARCHAR(32) NOT NULL DEFAULT 'open',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT ck_asset_import_issues_status CHECK (
                status IN ('open', 'resolved', 'ignored')
            )
        )
        """,
        """
        CREATE TABLE asset.audit_logs (
            id BIGSERIAL PRIMARY KEY,
            user_id INTEGER,
            action_type VARCHAR(64) NOT NULL,
            entity_type VARCHAR(64) NOT NULL,
            entity_id BIGINT,
            before_data JSONB,
            after_data JSONB,
            ip_address VARCHAR(64),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """,
        """
        CREATE OR REPLACE FUNCTION asset.enforce_image_tag_limit()
        RETURNS TRIGGER AS $$
        BEGIN
            PERFORM pg_advisory_xact_lock(NEW.image_id::bigint);

            IF (SELECT COUNT(*) FROM asset.image_tags WHERE image_id = NEW.image_id) >= 5 THEN
                RAISE EXCEPTION 'image % already has 5 tags', NEW.image_id
                    USING ERRCODE = 'check_violation';
            END IF;

            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """,
        """
        CREATE TRIGGER image_tags_limit
        BEFORE INSERT ON asset.image_tags
        FOR EACH ROW EXECUTE FUNCTION asset.enforce_image_tag_limit()
        """,
    ]

    for statement in statements:
        op.execute(statement)

    index_statements = [
        "CREATE INDEX ix_asset_images_category_id ON asset.images(category_id)",
        "CREATE INDEX ix_asset_images_status ON asset.images(status)",
        "CREATE INDEX ix_asset_images_category_capture_spectral "
        "ON asset.images(category_id, capture_type, spectral_type)",
        "CREATE INDEX ix_asset_image_sources_image_id ON asset.image_sources(image_id)",
        "CREATE INDEX ix_asset_image_sources_source_machine ON asset.image_sources(source_machine)",
        "CREATE INDEX ix_asset_annotation_files_batch_id ON asset.annotation_files(batch_id)",
        "CREATE INDEX ix_asset_annotation_files_image_id ON asset.annotation_files(image_id)",
        "CREATE INDEX ix_asset_annotation_files_match_status ON asset.annotation_files(match_status)",
        "CREATE INDEX ix_asset_image_tags_tag_id ON asset.image_tags(tag_id)",
        "CREATE INDEX ix_asset_import_items_batch_status ON asset.import_items(batch_id, status)",
        "CREATE INDEX ix_asset_import_issues_batch_status ON asset.import_issues(batch_id, status)",
        "CREATE INDEX ix_asset_import_issues_import_item_id ON asset.import_issues(import_item_id)",
        "CREATE INDEX ix_asset_audit_logs_entity_created ON asset.audit_logs(entity_type, entity_id, created_at)",
        "CREATE INDEX ix_asset_import_batches_status_created ON asset.import_batches(status, created_at)",
    ]

    for statement in index_statements:
        op.execute(statement)


def downgrade() -> None:
    op.execute("DROP SCHEMA IF EXISTS asset CASCADE")
