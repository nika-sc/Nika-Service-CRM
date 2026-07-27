-- Demo-only visitor / presence events (enabled via DEMO_VISITOR_STATS=1)
CREATE TABLE IF NOT EXISTS demo_visitor_events (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NULL,
    username TEXT NULL,
    ip TEXT NULL,
    user_agent TEXT NULL,
    path TEXT NULL,
    event_type TEXT NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_demo_visitor_events_created
    ON demo_visitor_events(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_demo_visitor_events_user_created
    ON demo_visitor_events(user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_demo_visitor_events_type_created
    ON demo_visitor_events(event_type, created_at DESC);
