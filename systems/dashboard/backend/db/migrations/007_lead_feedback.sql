CREATE TABLE IF NOT EXISTS lead_feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id INTEGER NOT NULL,
    action TEXT NOT NULL,          -- 'wrote' | 'spam'
    spam_reason TEXT,              -- from _analyze_spam_reason()
    gap_analysis TEXT,             -- JSON: patterns that should have caught it
    niche TEXT,
    vacancy_text TEXT,
    ts DATETIME DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_lead_feedback_lead_id ON lead_feedback(lead_id);
CREATE INDEX IF NOT EXISTS idx_lead_feedback_action ON lead_feedback(action);
