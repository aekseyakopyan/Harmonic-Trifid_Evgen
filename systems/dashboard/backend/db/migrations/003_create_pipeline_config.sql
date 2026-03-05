CREATE TABLE IF NOT EXISTS pipeline_config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT DEFAULT (datetime('now'))
);

INSERT OR IGNORE INTO pipeline_config (key, value) VALUES
    ('heuristic_hot_threshold', '70'),
    ('heuristic_warm_threshold', '40'),
    ('ml_min_score', '0.6'),
    ('llm_enabled', '1'),
    ('dedup_window_hours', '48'),
    ('stages_enabled', '{"hard_blocks":1,"dedup":1,"heuristic":1,"context":1,"ml":1,"llm":1}');

CREATE TABLE IF NOT EXISTS pipeline_blacklist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL CHECK(type IN ('word','channel','niche')),
    value TEXT NOT NULL UNIQUE,
    added_at TEXT DEFAULT (datetime('now'))
);
