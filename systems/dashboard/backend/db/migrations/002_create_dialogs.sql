CREATE TABLE IF NOT EXISTS dialogs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id INTEGER NOT NULL REFERENCES leads(id),
    channel TEXT NOT NULL,
    target_user TEXT,
    status TEXT DEFAULT 'pending',
    auto_mode INTEGER DEFAULT 1,
    last_message_at TEXT,
    started_at TEXT DEFAULT (datetime('now')),
    ended_at TEXT,
    result TEXT,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS dialog_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dialog_id INTEGER NOT NULL REFERENCES dialogs(id),
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    sent_at TEXT DEFAULT (datetime('now')),
    is_manual INTEGER DEFAULT 0
);
