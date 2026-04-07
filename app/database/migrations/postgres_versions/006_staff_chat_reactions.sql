CREATE TABLE IF NOT EXISTS staff_chat_reactions (
    id BIGSERIAL PRIMARY KEY,
    message_id BIGINT NOT NULL REFERENCES staff_chat_messages(id) ON DELETE CASCADE,
    user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    username TEXT NOT NULL,
    actor_display_name TEXT NOT NULL DEFAULT '',
    client_instance_id TEXT NOT NULL DEFAULT '',
    emoji TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_staff_chat_reactions_message
    ON staff_chat_reactions(message_id);

CREATE INDEX IF NOT EXISTS idx_staff_chat_reactions_message_emoji
    ON staff_chat_reactions(message_id, emoji);

CREATE UNIQUE INDEX IF NOT EXISTS uq_staff_chat_reactions_actor
    ON staff_chat_reactions(message_id, user_id, actor_display_name, client_instance_id, emoji);
