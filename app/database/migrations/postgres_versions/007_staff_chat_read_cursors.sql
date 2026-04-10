CREATE TABLE IF NOT EXISTS staff_chat_read_cursors (
    id BIGSERIAL PRIMARY KEY,
    room_key TEXT NOT NULL DEFAULT 'global',
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    username TEXT NOT NULL DEFAULT '',
    actor_display_name TEXT NOT NULL DEFAULT '',
    client_instance_id TEXT NOT NULL DEFAULT '',
    last_read_message_id BIGINT NOT NULL DEFAULT 0,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_staff_chat_read_cursors_actor
    ON staff_chat_read_cursors(room_key, user_id, actor_display_name, client_instance_id);

CREATE INDEX IF NOT EXISTS idx_staff_chat_read_cursors_room
    ON staff_chat_read_cursors(room_key);
