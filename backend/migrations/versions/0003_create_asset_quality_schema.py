"""Create quality precheck tables inside the existing asset schema.

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-20
"""

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    statements = [
        """
        CREATE TABLE asset.quality_profiles (
            id SERIAL PRIMARY KEY,
            profile_key VARCHAR(64) NOT NULL,
            capture_type VARCHAR(20),
            spectral_type VARCHAR(20),
            bit_depth INTEGER,
            version INTEGER NOT NULL DEFAULT 1,
            config JSONB NOT NULL DEFAULT '{}'::JSONB,
            status VARCHAR(32) NOT NULL DEFAULT 'active',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_asset_quality_profiles_key_version UNIQUE (profile_key, version),
            CONSTRAINT ck_asset_quality_profiles_capture_type CHECK (
                capture_type IS NULL OR capture_type IN ('photo', 'hand_drawn')
            ),
            CONSTRAINT ck_asset_quality_profiles_spectral_type CHECK (
                spectral_type IS NULL OR spectral_type IN ('visible', 'infrared')
            ),
            CONSTRAINT ck_asset_quality_profiles_status CHECK (
                status IN ('active', 'draft', 'disabled')
            )
        )
        """,
        """
        CREATE TABLE asset.quality_jobs (
            id BIGSERIAL PRIMARY KEY,
            batch_id BIGINT NOT NULL REFERENCES asset.import_batches(id) ON DELETE CASCADE,
            state VARCHAR(32) NOT NULL DEFAULT 'pending',
            total_count INTEGER NOT NULL DEFAULT 0 CHECK (total_count >= 0),
            processed_count INTEGER NOT NULL DEFAULT 0 CHECK (processed_count >= 0),
            error_count INTEGER NOT NULL DEFAULT 0 CHECK (error_count >= 0),
            retry_count INTEGER NOT NULL DEFAULT 0 CHECK (retry_count >= 0),
            error TEXT,
            started_at TIMESTAMPTZ,
            finished_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT ck_asset_quality_jobs_state CHECK (
                state IN ('pending', 'processing', 'completed', 'failed', 'cancelled')
            )
        )
        """,
        """
        CREATE TABLE asset.quality_candidates (
            id BIGSERIAL PRIMARY KEY,
            batch_id BIGINT NOT NULL REFERENCES asset.import_batches(id) ON DELETE CASCADE,
            normalized_relative_path TEXT NOT NULL,
            source_path TEXT NOT NULL,
            source_filename TEXT NOT NULL,
            source_machine TEXT,
            source_exists BOOLEAN NOT NULL DEFAULT TRUE,
            file_size BIGINT,
            mtime_ns BIGINT,
            sha256 CHAR(64),
            decode_status VARCHAR(32) NOT NULL DEFAULT 'pending',
            width INTEGER,
            height INTEGER,
            bit_depth INTEGER,
            channels INTEGER,
            color_mode VARCHAR(32),
            profile_key VARCHAR(64),
            phash_64 CHAR(16),
            existing_image_id BIGINT REFERENCES asset.images(id) ON DELETE SET NULL,
            duplicate_scope VARCHAR(16),
            exact_duplicate BOOLEAN NOT NULL DEFAULT FALSE,
            phash_min_distance SMALLINT,
            phash_nearest_image_id BIGINT REFERENCES asset.images(id) ON DELETE SET NULL,
            phash_nearest_candidate_id BIGINT REFERENCES asset.quality_candidates(id) ON DELETE SET NULL,
            similarity_coverage VARCHAR(32) NOT NULL DEFAULT 'none',
            source_fingerprint TEXT,
            status VARCHAR(32) NOT NULL DEFAULT 'pending',
            error_detail TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_asset_quality_candidates_batch_relative UNIQUE (
                batch_id, normalized_relative_path
            ),
            CONSTRAINT ck_asset_quality_candidates_decode_status CHECK (
                decode_status IN ('pending', 'ok', 'failed', 'unsupported')
            ),
            CONSTRAINT ck_asset_quality_candidates_status CHECK (
                status IN ('pending', 'processing', 'completed', 'failed', 'skipped')
            ),
            CONSTRAINT ck_asset_quality_candidates_duplicate_scope CHECK (
                duplicate_scope IS NULL OR duplicate_scope IN ('batch', 'library', 'both')
            ),
            CONSTRAINT ck_asset_quality_candidates_similarity_coverage CHECK (
                similarity_coverage IN ('none', 'partial', 'complete')
            )
        )
        """,
        """
        CREATE TABLE asset.quality_metric_results (
            id BIGSERIAL PRIMARY KEY,
            candidate_id BIGINT NOT NULL REFERENCES asset.quality_candidates(id) ON DELETE CASCADE,
            source_fingerprint TEXT NOT NULL,
            preprocess_version TEXT NOT NULL,
            algorithm_version TEXT NOT NULL,
            comparable BOOLEAN NOT NULL DEFAULT TRUE,
            metric_status VARCHAR(32) NOT NULL DEFAULT 'ok',
            lap_var DOUBLE PRECISION,
            tenengrad DOUBLE PRECISION,
            blur_effect DOUBLE PRECISION,
            rms_contrast DOUBLE PRECISION,
            p99_p1 DOUBLE PRECISION,
            mean_brightness DOUBLE PRECISION,
            dark_fraction DOUBLE PRECISION,
            bright_fraction DOUBLE PRECISION,
            noise_sigma DOUBLE PRECISION,
            noise_confidence DOUBLE PRECISION,
            entropy_8bit DOUBLE PRECISION,
            raw_min DOUBLE PRECISION,
            raw_max DOUBLE PRECISION,
            p01 DOUBLE PRECISION,
            p99 DOUBLE PRECISION,
            analysis_width INTEGER,
            analysis_height INTEGER,
            analysis_scale DOUBLE PRECISION,
            details JSONB NOT NULL DEFAULT '{}'::JSONB,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_asset_quality_metric_results_candidate_version UNIQUE (
                candidate_id, source_fingerprint, preprocess_version, algorithm_version
            ),
            CONSTRAINT ck_asset_quality_metric_results_status CHECK (
                metric_status IN ('ok', 'partial', 'unavailable')
            )
        )
        """,
        """
        CREATE TABLE asset.quality_library_phashes (
            image_id BIGINT PRIMARY KEY REFERENCES asset.images(id) ON DELETE CASCADE,
            phash_64 CHAR(16) NOT NULL,
            algorithm_version TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """,
        """
        CREATE TABLE asset.quality_neighbor_pairs (
            id BIGSERIAL PRIMARY KEY,
            batch_id BIGINT NOT NULL REFERENCES asset.import_batches(id) ON DELETE CASCADE,
            left_candidate_id BIGINT NOT NULL REFERENCES asset.quality_candidates(id) ON DELETE CASCADE,
            right_candidate_id BIGINT REFERENCES asset.quality_candidates(id) ON DELETE CASCADE,
            right_image_id BIGINT REFERENCES asset.images(id) ON DELETE CASCADE,
            phash_left CHAR(16) NOT NULL,
            phash_right CHAR(16) NOT NULL,
            distance SMALLINT NOT NULL,
            scope VARCHAR(32) NOT NULL,
            index_version TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_asset_quality_neighbor_pair UNIQUE (
                batch_id, left_candidate_id, right_candidate_id, right_image_id, scope, index_version
            ),
            CONSTRAINT ck_asset_quality_neighbor_pairs_scope CHECK (
                scope IN ('batch', 'library')
            ),
            CONSTRAINT ck_asset_quality_neighbor_pairs_distance CHECK (
                distance >= 0 AND distance <= 64
            ),
            CONSTRAINT ck_asset_quality_neighbor_pair_target CHECK (
                right_candidate_id IS NOT NULL OR right_image_id IS NOT NULL
            )
        )
        """,
        """
        CREATE TABLE asset.quality_evaluations (
            id BIGSERIAL PRIMARY KEY,
            batch_id BIGINT NOT NULL REFERENCES asset.import_batches(id) ON DELETE CASCADE,
            candidate_set_hash TEXT NOT NULL,
            filters JSONB NOT NULL DEFAULT '{}'::JSONB,
            profile_snapshots JSONB NOT NULL DEFAULT '{}'::JSONB,
            status VARCHAR(32) NOT NULL DEFAULT 'confirmed',
            created_by INTEGER,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT ck_asset_quality_evaluations_status CHECK (
                status IN ('draft', 'confirmed', 'expired')
            )
        )
        """,
        """
        CREATE TABLE asset.quality_evaluation_items (
            id BIGSERIAL PRIMARY KEY,
            evaluation_id BIGINT NOT NULL REFERENCES asset.quality_evaluations(id) ON DELETE CASCADE,
            candidate_id BIGINT NOT NULL REFERENCES asset.quality_candidates(id) ON DELETE CASCADE,
            recommendation VARCHAR(16) NOT NULL,
            flags JSONB NOT NULL DEFAULT '[]'::JSONB,
            manual_decision VARCHAR(16),
            CONSTRAINT uq_asset_quality_evaluation_items_eval_candidate UNIQUE (
                evaluation_id, candidate_id
            ),
            CONSTRAINT ck_asset_quality_evaluation_items_recommendation CHECK (
                recommendation IN ('admit', 'review', 'exclude')
            )
        )
        """,
        """
        CREATE TABLE asset.quality_manual_reviews (
            id BIGSERIAL PRIMARY KEY,
            candidate_id BIGINT NOT NULL REFERENCES asset.quality_candidates(id) ON DELETE CASCADE,
            decision VARCHAR(16) NOT NULL,
            note TEXT,
            reviewed_by INTEGER,
            reviewed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT ck_asset_quality_manual_reviews_decision CHECK (
                decision IN ('accepted', 'rejected', 'needs_review', 'cleared')
            )
        )
        """,
        """
        CREATE TABLE asset.quality_exports (
            id BIGSERIAL PRIMARY KEY,
            evaluation_id BIGINT NOT NULL REFERENCES asset.quality_evaluations(id) ON DELETE CASCADE,
            state VARCHAR(32) NOT NULL DEFAULT 'pending',
            storage_key TEXT,
            rules_storage_key TEXT,
            csv_filename TEXT,
            rules_filename TEXT,
            row_count INTEGER,
            file_sha256 TEXT,
            error TEXT,
            created_by INTEGER,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT ck_asset_quality_exports_state CHECK (
                state IN ('pending', 'processing', 'completed', 'failed')
            )
        )
        """,
    ]

    for statement in statements:
        op.execute(statement)

    index_statements = [
        "CREATE INDEX ix_asset_quality_jobs_state_created ON asset.quality_jobs(state, created_at)",
        "CREATE INDEX ix_asset_quality_candidates_batch_status ON asset.quality_candidates(batch_id, status)",
        "CREATE INDEX ix_asset_quality_candidates_sha256 ON asset.quality_candidates(sha256)",
        "CREATE INDEX ix_asset_quality_metric_results_candidate ON asset.quality_metric_results(candidate_id)",
        "CREATE INDEX ix_asset_quality_neighbor_pairs_batch ON asset.quality_neighbor_pairs(batch_id, scope)",
        "CREATE INDEX ix_asset_quality_neighbor_pairs_left ON asset.quality_neighbor_pairs(left_candidate_id)",
        "CREATE INDEX ix_asset_quality_evaluations_batch_created ON asset.quality_evaluations(batch_id, created_at)",
        "CREATE INDEX ix_asset_quality_evaluation_items_eval_recommendation "
        "ON asset.quality_evaluation_items(evaluation_id, recommendation)",
        "CREATE INDEX ix_asset_quality_manual_reviews_candidate_created "
        "ON asset.quality_manual_reviews(candidate_id, reviewed_at)",
        "CREATE INDEX ix_asset_quality_exports_evaluation_state "
        "ON asset.quality_exports(evaluation_id, state)",
    ]

    for statement in index_statements:
        op.execute(statement)


def downgrade() -> None:
    tables = [
        "quality_exports",
        "quality_manual_reviews",
        "quality_evaluation_items",
        "quality_evaluations",
        "quality_neighbor_pairs",
        "quality_library_phashes",
        "quality_metric_results",
        "quality_candidates",
        "quality_jobs",
        "quality_profiles",
    ]
    for table in tables:
        op.execute(f"DROP TABLE IF EXISTS asset.{table} CASCADE")
