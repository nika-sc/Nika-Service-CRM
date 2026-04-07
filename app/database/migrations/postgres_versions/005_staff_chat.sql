CREATE TABLE IF NOT EXISTS staff_chat_messages (
    id BIGSERIAL PRIMARY KEY,
    room_key TEXT NOT NULL DEFAULT 'global',
    user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    username TEXT NOT NULL,
    actor_display_name TEXT,
    client_instance_id TEXT,
    message_text TEXT,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    edited_at TIMESTAMP WITHOUT TIME ZONE,
    deleted_at TIMESTAMP WITHOUT TIME ZONE
);

CREATE TABLE IF NOT EXISTS staff_chat_attachments (
    id BIGSERIAL PRIMARY KEY,
    message_id BIGINT NOT NULL REFERENCES staff_chat_messages(id) ON DELETE CASCADE,
    original_name TEXT NOT NULL,
    stored_name TEXT NOT NULL,
    mime_type TEXT,
    size_bytes BIGINT NOT NULL CHECK (size_bytes >= 0),
    file_path TEXT NOT NULL,
    is_image SMALLINT NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_staff_chat_messages_room_created
    ON staff_chat_messages(room_key, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_staff_chat_messages_user_created
    ON staff_chat_messages(user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_staff_chat_attachments_message
    ON staff_chat_attachments(message_id);
