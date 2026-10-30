"""
SQLite DDL statements for MenuMind AI.
"""

CREATE_TABLES_SQL = [
    # ── Restaurants ─────────────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS restaurants (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        name        TEXT NOT NULL,
        city        TEXT,
        location    TEXT,
        website     TEXT,
        category    TEXT,
        created_at  TEXT DEFAULT (datetime('now'))
    )
    """,

    # ── Analysis Runs ────────────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS analysis_runs (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        restaurant_id   INTEGER NOT NULL REFERENCES restaurants(id),
        period_start    TEXT,
        period_end      TEXT,
        status          TEXT DEFAULT 'pending',
        created_at      TEXT DEFAULT (datetime('now')),
        completed_at    TEXT,
        data_quality_score REAL,
        notes           TEXT
    )
    """,

    # ── Uploaded File Metadata ───────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS data_files (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id          INTEGER NOT NULL REFERENCES analysis_runs(id),
        file_type       TEXT NOT NULL,   -- menu, sales, reviews, costs
        original_name   TEXT,
        row_count       INTEGER,
        accepted_rows   INTEGER,
        rejected_rows   INTEGER,
        uploaded_at     TEXT DEFAULT (datetime('now'))
    )
    """,

    # ── Recommendations ──────────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS recommendations (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id              INTEGER NOT NULL REFERENCES analysis_runs(id),
        item_id             TEXT,
        item_name           TEXT NOT NULL,
        action              TEXT NOT NULL,  -- IMPROVE/REMOVE/PROMOTE/REPRICE/INSUFFICIENT_EVIDENCE
        priority            TEXT,           -- high/medium/low
        confidence_score    REAL,
        reasoning           TEXT,
        alternative_actions TEXT,           -- JSON list
        expected_benefits   TEXT,
        potential_risks     TEXT,
        missing_information TEXT,
        next_steps          TEXT,           -- JSON list
        sales_metrics       TEXT,           -- JSON blob
        review_themes       TEXT,           -- JSON blob
        profitability       TEXT,           -- JSON blob
        requires_approval   INTEGER DEFAULT 1,
        success_metrics     TEXT,
        created_at          TEXT DEFAULT (datetime('now'))
    )
    """,

    # ── Approval Decisions ───────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS approvals (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        recommendation_id   INTEGER NOT NULL REFERENCES recommendations(id),
        decision            TEXT NOT NULL,  -- approved/rejected/saved_for_later
        decided_by          TEXT DEFAULT 'user',
        notes               TEXT,
        decided_at          TEXT DEFAULT (datetime('now'))
    )
    """,

    # ── Experiments ──────────────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS experiments (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        recommendation_id   INTEGER REFERENCES recommendations(id),
        run_id              INTEGER NOT NULL REFERENCES analysis_runs(id),
        title               TEXT NOT NULL,
        hypothesis          TEXT,
        intervention        TEXT,
        baseline_start      TEXT,
        baseline_end        TEXT,
        test_start          TEXT,
        test_end            TEXT,
        success_criteria    TEXT,
        guardrail_metrics   TEXT,
        status              TEXT DEFAULT 'proposed',  -- proposed/approved/active/completed/cancelled
        created_at          TEXT DEFAULT (datetime('now')),
        approved_at         TEXT
    )
    """,

    # ── Experiment Results ───────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS experiment_results (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        experiment_id   INTEGER NOT NULL REFERENCES experiments(id),
        metric_name     TEXT NOT NULL,
        baseline_value  REAL,
        test_value      REAL,
        change_pct      REAL,
        notes           TEXT,
        recorded_at     TEXT DEFAULT (datetime('now'))
    )
    """,


    # ── Food Waste ──────────────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS waste_records (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id              INTEGER NOT NULL REFERENCES analysis_runs(id),
        ingredient_name     TEXT NOT NULL,
        quantity            REAL,
        unit                TEXT DEFAULT 'kg',
        unit_cost           REAL,
        waste_reason        TEXT,
        associated_dish     TEXT,
        image_item_name     TEXT,
        image_confidence    REAL,
        verified_by_user    INTEGER DEFAULT 0,
        created_at          TEXT DEFAULT (datetime('now'))
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS waste_images (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id              INTEGER NOT NULL REFERENCES analysis_runs(id),
        original_name       TEXT,
        mime_type           TEXT,
        detected_items      TEXT,
        limitations         TEXT,
        created_at          TEXT DEFAULT (datetime('now'))
    )
    """,

    # ── Review Retrieval Metadata ─────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS retrieval_metadata (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id          INTEGER NOT NULL REFERENCES analysis_runs(id),
        source          TEXT NOT NULL,
        source_url      TEXT,
        review_count    INTEGER DEFAULT 0,
        retrieved_at    TEXT DEFAULT (datetime('now')),
        attribution     TEXT,
        limitations     TEXT
    )
    """,

    # ── AI Conversations & Messages (Additive) ───────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS ai_conversations (
        id              TEXT PRIMARY KEY,
        restaurant_id   INTEGER NOT NULL REFERENCES restaurants(id),
        run_id          INTEGER REFERENCES analysis_runs(id),
        title           TEXT NOT NULL,
        created_at      TEXT DEFAULT (datetime('now')),
        updated_at      TEXT DEFAULT (datetime('now'))
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS ai_messages (
        id              TEXT PRIMARY KEY,
        conversation_id TEXT NOT NULL REFERENCES ai_conversations(id) ON DELETE CASCADE,
        role            TEXT NOT NULL,
        content         TEXT NOT NULL,
        attachments     TEXT,
        agent_metadata  TEXT,
        created_at      TEXT DEFAULT (datetime('now'))
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS ai_generated_assets (
        id              TEXT PRIMARY KEY,
        conversation_id TEXT REFERENCES ai_conversations(id),
        restaurant_id   INTEGER NOT NULL REFERENCES restaurants(id),
        asset_type      TEXT NOT NULL,
        title           TEXT NOT NULL,
        content         TEXT,
        image_url       TEXT,
        status          TEXT DEFAULT 'draft',
        created_at      TEXT DEFAULT (datetime('now')),
        updated_at      TEXT DEFAULT (datetime('now'))
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS ai_agent_runs (
        id              TEXT PRIMARY KEY,
        conversation_id TEXT REFERENCES ai_conversations(id),
        restaurant_id   INTEGER NOT NULL REFERENCES restaurants(id),
        agent_name      TEXT NOT NULL,
        intent          TEXT,
        tools_invoked   TEXT,
        status          TEXT DEFAULT 'completed',
        execution_time_ms INTEGER,
        created_at      TEXT DEFAULT (datetime('now'))
    )
    """,
]
