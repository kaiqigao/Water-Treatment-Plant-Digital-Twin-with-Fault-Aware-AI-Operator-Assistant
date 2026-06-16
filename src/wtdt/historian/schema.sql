CREATE TABLE IF NOT EXISTS tag_samples (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp_utc TEXT NOT NULL,
    tag TEXT NOT NULL,
    value TEXT NOT NULL,
    quality TEXT NOT NULL DEFAULT 'good',
    source TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_tag_samples_tag_time
ON tag_samples(tag, timestamp_utc);
