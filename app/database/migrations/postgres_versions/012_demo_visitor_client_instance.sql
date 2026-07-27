-- Distinguish browser sessions for demo online stats (same login, different browsers)
ALTER TABLE demo_visitor_events
    ADD COLUMN IF NOT EXISTS client_instance_id TEXT NULL;

CREATE INDEX IF NOT EXISTS idx_demo_visitor_events_client_created
    ON demo_visitor_events(client_instance_id, created_at DESC);
