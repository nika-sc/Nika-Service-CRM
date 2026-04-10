(() => {
    const ROOM_KEY = "global";
    const NS = "/staff-chat";
    const ALWAYS_OPEN = false;
    const START_OPEN = true;
    const STORAGE_ACTOR = `staff_chat_actor_${window.currentUserId || "anon"}`;
    const STORAGE_CLIENT = `staff_chat_client_${window.currentUserId || "anon"}`;
    const STORAGE_PANEL_OPEN = `staff_chat_open_${window.currentUserId || "anon"}`;
    const MAX_HISTORY_LIMIT = 40;
    const SYNC_INTERVAL_MS = 12000;
    const REACTION_SET = ["👍", "❤️", "😂", "😮", "😢", "🔥", "✅", "👀"];

    const state = {
        socket: null,
        isOpen: false,
        unread: 0,
        loadingOld: false,
        oldestId: null,
        newestId: null,
        actorName: "",
        clientInstanceId: "",
        selectedFiles: [],
        connected: false,
        localTypingTimer: null,
        remoteTypingTimer: null,
        lastTypingEmitAt: 0,
        remoteTypingText: "",
        limits: {
            maxFiles: 8,
            maxFileSizeMb: 20,
        },
        syncTimer: null,
        syncInFlight: false,
        hasSocketStream: false,
        incomingAudio: null,
        audioUnlocked: false,
        pendingIncomingSound: false,
        audioUnlockHandler: null,
        emojiPickerOpen: false,
        myReactions: new Map(),
        openReactionMenuMessageId: null,
    };

    function ready() {
        if (!window.currentUserId || !window.staffChatEnabled) return;
        bindElements();
        restoreIdentity();
        initIncomingSound();
        initSocket();
        setPanelOpen(restorePanelState());
        loadHistory();
        startPeriodicSync();
    }

    function el(id) {
        return document.getElementById(id);
    }

    function bindElements() {
        const fab = el("staffChatFab");
        const closeBtn = el("staffChatClose");
        const saveIdentityBtn = el("staffChatSaveIdentity");
        const sendBtn = el("staffChatSend");
        const emojiToggleBtn = el("staffChatEmojiToggleBtn");
        const emojiPicker = el("staffChatEmojiPicker");
        const attachBtn = el("staffChatAttachBtn");
        const fileInput = el("staffChatFileInput");
        const messages = el("staffChatMessages");
        const input = el("staffChatInput");

        if (fab) fab.addEventListener("click", togglePanel);
        if (closeBtn) closeBtn.addEventListener("click", () => setPanelOpen(false));
        if (saveIdentityBtn) saveIdentityBtn.addEventListener("click", saveIdentity);
        if (sendBtn) sendBtn.addEventListener("click", sendCurrentMessage);
        if (emojiToggleBtn) emojiToggleBtn.addEventListener("click", toggleEmojiPicker);
        if (emojiPicker) emojiPicker.addEventListener("click", onEmojiPickerClick);
        if (attachBtn) attachBtn.addEventListener("click", () => fileInput && fileInput.click());
        if (fileInput) fileInput.addEventListener("change", onFileSelected);
        if (messages) messages.addEventListener("scroll", onMessagesScroll);
        document.addEventListener("click", onDocumentClick);
        if (input) {
            input.addEventListener("input", onComposerInput);
            input.addEventListener("keydown", onComposerKeyDown);
        }
    }

    function restoreIdentity() {
        let actor = localStorage.getItem(STORAGE_ACTOR) || "";
        if (!actor && window.currentUserRole === "manager") {
            actor = "Менеджер";
        }
        const actorInput = el("staffChatActorName");
        if (actorInput) {
            actorInput.value = actor;
        }
        state.actorName = actor;

        let clientId = localStorage.getItem(STORAGE_CLIENT) || "";
        if (!clientId) {
            clientId = (window.crypto && window.crypto.randomUUID)
                ? window.crypto.randomUUID()
                : `client_${Date.now()}_${Math.random().toString(16).slice(2)}`;
            localStorage.setItem(STORAGE_CLIENT, clientId);
        }
        state.clientInstanceId = clientId;
    }

    function saveIdentity() {
        const actorInput = el("staffChatActorName");
        const actor = (actorInput ? actorInput.value : "").trim();
        if (!actor) {
            showStatus("Укажите, кто пишет с этого ПК");
            return;
        }
        state.actorName = actor;
        localStorage.setItem(STORAGE_ACTOR, actor);
        showStatus("Подпись сохранена");
    }

    function togglePanel() {
        setPanelOpen(!state.isOpen);
    }

    function setPanelOpen(open) {
        if (ALWAYS_OPEN) open = true;
        state.isOpen = !!open;
        persistPanelState();
        const panel = el("staffChatPanel");
        const fab = el("staffChatFab");
        if (panel) {
            panel.classList.toggle("is-hidden", !state.isOpen);
        }
        if (fab) {
            fab.style.display = state.isOpen ? "none" : "";
        }
        if (state.isOpen) {
            state.unread = 0;
            updateUnreadBadge();
            scrollToBottom();
            const ta = el("staffChatInput");
            if (ta) ta.focus();
        } else {
            setEmojiPickerOpen(false);
            setReactionMenuOpen(null);
        }
    }

    function restorePanelState() {
        if (ALWAYS_OPEN) return true;
        try {
            const raw = localStorage.getItem(STORAGE_PANEL_OPEN);
            if (raw === "1") return true;
            if (raw === "0") return false;
        } catch (_) {
            // localStorage может быть недоступен
        }
        return START_OPEN;
    }

    function persistPanelState() {
        if (ALWAYS_OPEN) return;
        try {
            localStorage.setItem(STORAGE_PANEL_OPEN, state.isOpen ? "1" : "0");
        } catch (_) {
            // localStorage может быть недоступен
        }
    }

    function initSocket() {
        if (typeof window.io !== "function") {
            showStatus("Socket.IO не загружен, чат работает в ограниченном режиме");
            return;
        }
        const socket = window.io(NS, {
            // Для встроенного dev-сервера websocket может шуметь 500 в логах.
            // Polling-transport стабильнее в текущем окружении.
            transports: ["polling"],
            reconnection: true,
            reconnectionDelayMax: 7000,
        });
        state.socket = socket;

        socket.on("connect", () => {
            state.connected = true;
            state.hasSocketStream = true;
            socket.emit("join_room", { room_key: ROOM_KEY });
            showStatus("Подключено");
        });
        socket.on("disconnect", () => {
            state.connected = false;
            state.hasSocketStream = false;
            showStatus("Realtime отключен, работает авто-синхронизация...");
        });
        socket.on("chat_error", (payload) => {
            showStatus((payload && payload.error) || "Ошибка чата");
        });
        socket.on("message_created", (payload) => {
            if (!payload || !payload.message) return;
            appendMessage(payload.message, true);
        });
        socket.on("message_updated", (payload) => {
            if (!payload || !payload.message) return;
            updateMessageInDom(payload.message, true);
        });
        socket.on("message_deleted", (payload) => {
            const id = payload && payload.message_id;
            if (!id) return;
            removeMessageFromDom(Number(id));
        });
        socket.on("typing", (payload) => {
            if (!payload) return;
            const sameClient = (payload.client_instance_id || "") === state.clientInstanceId;
            if (sameClient) return;
            if (payload.is_typing && payload.actor_display_name) {
                state.remoteTypingText = `${payload.actor_display_name} печатает...`;
                renderTyping();
                clearTimeout(state.remoteTypingTimer);
                state.remoteTypingTimer = setTimeout(() => {
                    state.remoteTypingText = "";
                    renderTyping();
                }, 1800);
            } else {
                state.remoteTypingText = "";
                renderTyping();
            }
        });
    }

    function startPeriodicSync() {
        if (state.syncTimer) return;
        state.syncTimer = setInterval(syncLatestMessages, SYNC_INTERVAL_MS);
    }

    async function syncLatestMessages() {
        // Если realtime канал уже тянет события — лишний polling не нужен.
        if (state.hasSocketStream) return;
        if (state.syncInFlight) return;
        state.syncInFlight = true;
        try {
            const query = new URLSearchParams();
            query.set("limit", "25");
            query.set("room_key", ROOM_KEY);
            query.set("actor_display_name", state.actorName || "");
            query.set("client_instance_id", state.clientInstanceId || "");
            const resp = await fetch(`/api/staff-chat/history?${query.toString()}`);
            const data = await resp.json();
            if (!data || !data.success) return;
            const list = Array.isArray(data.messages) ? data.messages : [];
            if (!list.length) return;
            const sorted = list.slice().sort((a, b) => Number(a.id || 0) - Number(b.id || 0));
            sorted.forEach((m) => {
                if (!m || !m.id) return;
                if (!state.newestId || Number(m.id) > Number(state.newestId)) {
                    appendMessage(m, true);
                }
            });
        } catch (e) {
            // Тихий fallback: просто пропускаем текущий цикл
        } finally {
            state.syncInFlight = false;
        }
    }

    async function loadHistory(beforeId = null) {
        if (state.loadingOld) return;
        state.loadingOld = true;
        try {
            const query = new URLSearchParams();
            query.set("limit", String(MAX_HISTORY_LIMIT));
            if (beforeId) query.set("before_id", String(beforeId));
            query.set("room_key", ROOM_KEY);
            query.set("actor_display_name", state.actorName || "");
            query.set("client_instance_id", state.clientInstanceId || "");
            const resp = await fetch(`/api/staff-chat/history?${query.toString()}`);
            const data = await resp.json();
            if (!data.success) throw new Error(data.error || "history_failed");
            const messages = Array.isArray(data.messages) ? data.messages : [];
            if (data.limits) {
                const maxFiles = Number(data.limits.max_files_per_message || 8);
                const maxFileSizeBytes = Number(data.limits.max_file_size_bytes || (20 * 1024 * 1024));
                state.limits.maxFiles = maxFiles;
                state.limits.maxFileSizeMb = Math.max(1, Math.round(maxFileSizeBytes / (1024 * 1024)));
                const hint = el("staffChatLimitsHint");
                if (hint) hint.textContent = `Лимиты: до ${state.limits.maxFiles} файлов, до ${state.limits.maxFileSizeMb} MB на файл.`;
            }
            if (!messages.length) return;
            prependMessages(messages, !!beforeId);
        } catch (e) {
            console.error("chat history load failed", e);
            showStatus("Не удалось загрузить историю");
        } finally {
            state.loadingOld = false;
        }
    }

    function onMessagesScroll() {
        const box = el("staffChatMessages");
        if (!box || state.loadingOld) return;
        if (box.scrollTop <= 40 && state.oldestId) {
            loadHistory(state.oldestId);
        }
    }

    function prependMessages(messages, keepPosition) {
        const box = el("staffChatMessages");
        if (!box) return;
        const prevHeight = box.scrollHeight;
        const frag = document.createDocumentFragment();
        messages.forEach((m) => {
            const node = buildMessageNode(m);
            frag.appendChild(node);
            updateBounds(m);
        });
        box.insertBefore(frag, box.firstChild);
        if (!keepPosition) {
            box.scrollTop = box.scrollHeight;
        } else {
            box.scrollTop = box.scrollHeight - prevHeight;
        }
    }

    function appendMessage(message, fromSocket) {
        const box = el("staffChatMessages");
        if (!box || !message || !message.id) return;
        if (state.newestId && Number(message.id) <= Number(state.newestId)) return;

        if (!fromSocket) {
            absorbServerOwnReactions(message);
        }
        const own = isOwnMessage(message);
        const node = buildMessageNode(message, !fromSocket);
        box.appendChild(node);
        updateBounds(message);

        if (fromSocket) {
            if (!own) {
                playIncomingSound();
                if (!state.isOpen) {
                    setPanelOpen(true);
                }
            }
        }

        if (state.isOpen) {
            scrollToBottom();
        } else if (fromSocket) {
            state.unread += 1;
            updateUnreadBadge();
        }
    }

    function updateBounds(message) {
        const id = Number(message.id);
        if (!state.oldestId || id < Number(state.oldestId)) state.oldestId = id;
        if (!state.newestId || id > Number(state.newestId)) state.newestId = id;
    }

    function buildMessageNode(message, trustServerOwnFlags = true) {
        const item = document.createElement("div");
        item.className = "staff-chat-message";
        item.dataset.messageId = String(message.id);
        const mine = isOwnMessage(message);
        if (mine) item.classList.add("mine");

        const author = document.createElement("div");
        author.className = "staff-chat-author";
        author.textContent = message.actor_display_name || message.username || "Сотрудник";
        item.appendChild(author);

        const metaRow = document.createElement("div");
        metaRow.className = "staff-chat-meta-row";
        const meta = document.createElement("div");
        meta.className = "staff-chat-meta";
        const via = message.username ? `через ${message.username}` : "";
        const edited = message.edited_at ? " (изменено)" : "";
        meta.textContent = `${formatDateTime(message.created_at)}${via ? ` · ${via}` : ""}`;
        meta.textContent += edited;
        metaRow.appendChild(meta);
        if (mine) {
            const actions = document.createElement("div");
            actions.className = "staff-chat-message-actions";
            const editBtn = document.createElement("button");
            editBtn.type = "button";
            editBtn.className = "staff-chat-action-btn";
            editBtn.textContent = "Изм.";
            editBtn.addEventListener("click", () => startEditMessage(message));
            actions.appendChild(editBtn);
            const delBtn = document.createElement("button");
            delBtn.type = "button";
            delBtn.className = "staff-chat-action-btn";
            delBtn.textContent = "Удал.";
            delBtn.addEventListener("click", () => deleteMessage(message));
            actions.appendChild(delBtn);
            metaRow.appendChild(actions);
        }
        item.appendChild(metaRow);

        if (message.message_text) {
            const text = document.createElement("div");
            text.className = "staff-chat-text";
            text.textContent = message.message_text;
            item.appendChild(text);
        }

        const attachments = Array.isArray(message.attachments) ? message.attachments : [];
        if (attachments.length) {
            const list = document.createElement("div");
            list.className = "staff-chat-attachments";
            attachments.forEach((att) => {
                const link = document.createElement("a");
                link.className = "staff-chat-attachment";
                link.href = att.url;
                link.target = "_blank";
                link.rel = "noopener noreferrer";
                link.textContent = att.original_name || `Файл #${att.id}`;
                list.appendChild(link);

                if (att.is_image) {
                    const img = document.createElement("img");
                    img.className = "staff-chat-image";
                    img.src = att.url;
                    img.alt = att.original_name || "Изображение";
                    list.appendChild(img);
                }
            });
            item.appendChild(list);
        }

        const reactions = Array.isArray(message.reactions) ? message.reactions : [];
        const reactionMap = new Map();
        reactions.forEach((r) => {
            if (!r || !r.emoji) return;
            reactionMap.set(r.emoji, {
                count: Number(r.count || 0),
                reactedByMe: !!r.reacted_by_me,
            });
        });
        const ownSet = getMyReactionsForMessage(message.id);

        const reactionsRow = document.createElement("div");
        reactionsRow.className = "staff-chat-reactions";
        REACTION_SET.forEach((emoji) => {
            const info = reactionMap.get(emoji) || { count: 0, reactedByMe: false };
            if (info.count <= 0) return;
            const btn = document.createElement("button");
            btn.type = "button";
            btn.className = "staff-chat-reaction-btn";
            const active = ownSet.has(emoji) || (trustServerOwnFlags && info.reactedByMe);
            if (active) btn.classList.add("active");
            btn.title = "Реакция";
            btn.innerHTML = `<span class="emoji">${emoji}</span><span class="count">${info.count > 0 ? info.count : ""}</span>`;
            btn.addEventListener("click", () => toggleReaction(message.id, emoji));
            reactionsRow.appendChild(btn);
        });

        const toggleBtn = document.createElement("button");
        toggleBtn.type = "button";
        toggleBtn.className = "staff-chat-reaction-toggle";
        toggleBtn.textContent = "Реакция";
        toggleBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            toggleReactionMenu(message.id);
        });
        reactionsRow.appendChild(toggleBtn);

        const menu = document.createElement("div");
        menu.className = "staff-chat-reaction-menu is-hidden";
        menu.dataset.messageId = String(message.id);
        menu.addEventListener("click", (e) => {
            e.stopPropagation();
        });
        REACTION_SET.forEach((emoji) => {
            const menuBtn = document.createElement("button");
            menuBtn.type = "button";
            menuBtn.className = "staff-chat-reaction-menu-btn";
            menuBtn.textContent = emoji;
            menuBtn.addEventListener("click", () => {
                setReactionMenuOpen(null);
                toggleReaction(message.id, emoji);
            });
            menu.appendChild(menuBtn);
        });
        reactionsRow.appendChild(menu);
        item.appendChild(reactionsRow);

        return item;
    }

    function updateMessageInDom(message, fromRealtime = false) {
        const box = el("staffChatMessages");
        if (!box || !message || !message.id) return;
        if (!fromRealtime) {
            absorbServerOwnReactions(message);
        }
        const old = box.querySelector(`.staff-chat-message[data-message-id="${message.id}"]`);
        const replacement = buildMessageNode(message, !fromRealtime);
        if (old) {
            old.replaceWith(replacement);
        } else {
            appendMessage(message, fromRealtime);
        }
        scrollToBottom();
    }

    function removeMessageFromDom(messageId) {
        const box = el("staffChatMessages");
        if (!box) return;
        const node = box.querySelector(`.staff-chat-message[data-message-id="${messageId}"]`);
        if (node) node.remove();
        state.myReactions.delete(String(messageId));
    }

    async function sendCurrentMessage() {
        const ta = el("staffChatInput");
        const messageText = (ta ? ta.value : "").trim();
        if (!state.actorName) {
            showStatus("Сначала укажите, кто вы");
            return;
        }
        if (!messageText && !state.selectedFiles.length) {
            return;
        }
        if (state.selectedFiles.length) {
            await sendWithFiles(messageText);
            if (ta) ta.value = "";
            return;
        }
        if (state.socket && state.connected) {
            state.socket.emit("send_message", {
                room_key: ROOM_KEY,
                actor_display_name: state.actorName,
                client_instance_id: state.clientInstanceId,
                message_text: messageText,
            });
            if (ta) ta.value = "";
            emitTyping(false);
            return;
        }
        await sendViaHttp(messageText);
        if (ta) ta.value = "";
        emitTyping(false);
    }

    async function sendViaHttp(messageText) {
        try {
            const resp = await fetch("/api/staff-chat/send", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    room_key: ROOM_KEY,
                    actor_display_name: state.actorName,
                    client_instance_id: state.clientInstanceId,
                    message_text: messageText,
                }),
            });
            const data = await resp.json();
            if (!data.success) throw new Error(data.error || "send_failed");
            appendMessage(data.message, false);
            scrollToBottom();
        } catch (e) {
            console.error("send message failed", e);
            showStatus("Не удалось отправить сообщение");
        }
    }

    async function sendWithFiles(messageText) {
        try {
            const form = new FormData();
            form.append("room_key", ROOM_KEY);
            form.append("actor_display_name", state.actorName);
            form.append("client_instance_id", state.clientInstanceId);
            form.append("message_text", messageText);
            state.selectedFiles.forEach((f) => form.append("files", f, f.name));

            const data = await uploadWithProgress(form);
            if (!data.success) throw new Error(data.error || "upload_failed");
            clearSelectedFiles();
            if (!state.socket || !state.connected) {
                appendMessage(data.message, false);
                scrollToBottom();
            }
        } catch (e) {
            console.error("upload message failed", e);
            showStatus("Ошибка загрузки файла");
        }
    }

    function onFileSelected(e) {
        const input = e.target;
        let files = Array.from(input.files || []);
        if (files.length > state.limits.maxFiles) {
            files = files.slice(0, state.limits.maxFiles);
            showStatus(`Можно приложить не более ${state.limits.maxFiles} файлов`);
        }
        const tooLarge = files.find((f) => f.size > state.limits.maxFileSizeMb * 1024 * 1024);
        if (tooLarge) {
            showStatus(`Файл ${tooLarge.name} больше ${state.limits.maxFileSizeMb} MB`);
            files = files.filter((f) => f.size <= state.limits.maxFileSizeMb * 1024 * 1024);
        }
        state.selectedFiles = files;
        renderSelectedFiles();
    }

    function clearSelectedFiles() {
        state.selectedFiles = [];
        const input = el("staffChatFileInput");
        if (input) input.value = "";
        renderSelectedFiles();
    }

    function renderSelectedFiles() {
        const box = el("staffChatFileList");
        if (!box) return;
        if (!state.selectedFiles.length) {
            box.textContent = "";
            return;
        }
        box.textContent = state.selectedFiles.map((f) => `${f.name} (${formatBytes(f.size)})`).join(" | ");
    }

    function onComposerInput() {
        emitTyping(true);
        clearTimeout(state.localTypingTimer);
        state.localTypingTimer = setTimeout(() => emitTyping(false), 1200);
    }

    function onComposerKeyDown(e) {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            sendCurrentMessage();
        }
    }

    function toggleReaction(messageId, emoji) {
        if (!state.actorName) {
            showStatus("Сначала укажите, кто вы");
            return;
        }
        toggleLocalReaction(messageId, emoji);
        if (state.socket && state.connected) {
            state.socket.emit("toggle_reaction", {
                message_id: messageId,
                actor_display_name: state.actorName,
                client_instance_id: state.clientInstanceId,
                emoji,
            });
            return;
        }
        fetch(`/api/staff-chat/message/${messageId}/reaction`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                actor_display_name: state.actorName,
                client_instance_id: state.clientInstanceId,
                emoji,
            }),
        }).then((r) => r.json()).then((data) => {
            if (!data.success) throw new Error(data.error || "reaction_failed");
            updateMessageInDom(data.message);
        }).catch((e) => {
            console.error("toggle reaction failed", e);
            toggleLocalReaction(messageId, emoji);
            showStatus("Не удалось поставить реакцию");
        });
    }

    function toggleReactionMenu(messageId) {
        const key = String(messageId);
        if (state.openReactionMenuMessageId === key) {
            setReactionMenuOpen(null);
            return;
        }
        setReactionMenuOpen(key);
    }

    function setReactionMenuOpen(messageId) {
        state.openReactionMenuMessageId = messageId ? String(messageId) : null;
        const menus = document.querySelectorAll(".staff-chat-reaction-menu");
        menus.forEach((menu) => {
            const owner = menu.getAttribute("data-message-id") || "";
            menu.classList.toggle("is-hidden", owner !== state.openReactionMenuMessageId);
        });
    }

    function absorbServerOwnReactions(message) {
        if (!message || !message.id) return;
        const set = getMyReactionsForMessage(message.id);
        const reactions = Array.isArray(message.reactions) ? message.reactions : [];
        reactions.forEach((r) => {
            if (r && r.emoji && r.reacted_by_me) {
                set.add(r.emoji);
            }
        });
    }

    function toggleLocalReaction(messageId, emoji) {
        const set = getMyReactionsForMessage(messageId);
        if (set.has(emoji)) {
            set.delete(emoji);
        } else {
            set.add(emoji);
        }
    }

    function getMyReactionsForMessage(messageId) {
        const key = String(messageId);
        if (!state.myReactions.has(key)) {
            state.myReactions.set(key, new Set());
        }
        return state.myReactions.get(key);
    }

    function toggleEmojiPicker() {
        setEmojiPickerOpen(!state.emojiPickerOpen);
    }

    function setEmojiPickerOpen(open) {
        state.emojiPickerOpen = !!open;
        const picker = el("staffChatEmojiPicker");
        if (!picker) return;
        picker.classList.toggle("is-hidden", !state.emojiPickerOpen);
    }

    function onEmojiPickerClick(e) {
        const target = e.target instanceof Element ? e.target.closest("[data-emoji]") : null;
        if (!target) return;
        const emoji = target.getAttribute("data-emoji") || "";
        if (!emoji) return;
        insertEmojiAtCursor(emoji);
    }

    function insertEmojiAtCursor(emoji) {
        const ta = el("staffChatInput");
        if (!ta) return;
        const current = ta.value || "";
        const start = Number.isInteger(ta.selectionStart) ? ta.selectionStart : current.length;
        const end = Number.isInteger(ta.selectionEnd) ? ta.selectionEnd : current.length;
        ta.value = `${current.slice(0, start)}${emoji}${current.slice(end)}`;
        const cursor = start + emoji.length;
        ta.focus();
        ta.setSelectionRange(cursor, cursor);
        onComposerInput();
    }

    function onDocumentClick(e) {
        const target = e.target;
        if (!(target instanceof Node)) return;
        if (state.emojiPickerOpen) {
            const picker = el("staffChatEmojiPicker");
            const toggleBtn = el("staffChatEmojiToggleBtn");
            const insidePicker = !!picker && picker.contains(target);
            const insideToggle = !!toggleBtn && toggleBtn.contains(target);
            if (!insidePicker && !insideToggle) {
                setEmojiPickerOpen(false);
            }
        }
        if (state.openReactionMenuMessageId) {
            const insideReactions = target instanceof Element && !!target.closest(".staff-chat-reactions");
            if (!insideReactions) {
                setReactionMenuOpen(null);
            }
        }
    }

    function emitTyping(isTyping) {
        if (!state.socket || !state.connected || !state.actorName) return;
        const now = Date.now();
        if (isTyping && now - state.lastTypingEmitAt < 800) return;
        state.lastTypingEmitAt = now;
        state.socket.emit("typing", {
            room_key: ROOM_KEY,
            actor_display_name: state.actorName,
            client_instance_id: state.clientInstanceId,
            is_typing: !!isTyping,
        });
    }

    function renderTyping() {
        const node = el("staffChatTyping");
        if (!node) return;
        node.textContent = state.remoteTypingText || "";
    }

    function startEditMessage(message) {
        const current = message.message_text || "";
        const updated = window.prompt("Редактирование сообщения", current);
        if (updated === null) return;
        const clean = updated.trim();
        if (!clean) {
            showStatus("Пустое сообщение нельзя сохранить");
            return;
        }
        if (state.socket && state.connected) {
            state.socket.emit("edit_message", {
                message_id: message.id,
                actor_display_name: state.actorName,
                client_instance_id: state.clientInstanceId,
                message_text: clean,
            });
            return;
        }
        fetch(`/api/staff-chat/message/${message.id}`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                actor_display_name: state.actorName,
                client_instance_id: state.clientInstanceId,
                message_text: clean,
            }),
        }).then((r) => r.json()).then((data) => {
            if (!data.success) throw new Error(data.error || "edit_failed");
            updateMessageInDom(data.message);
        }).catch((e) => {
            console.error("edit message failed", e);
            showStatus("Не удалось изменить сообщение");
        });
    }

    function deleteMessage(message) {
        if (!window.confirm("Удалить это сообщение?")) return;
        if (state.socket && state.connected) {
            state.socket.emit("delete_message", {
                message_id: message.id,
                actor_display_name: state.actorName,
                client_instance_id: state.clientInstanceId,
            });
            return;
        }
        fetch(`/api/staff-chat/message/${message.id}`, {
            method: "DELETE",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                actor_display_name: state.actorName,
                client_instance_id: state.clientInstanceId,
            }),
        }).then((r) => r.json()).then((data) => {
            if (!data.success) throw new Error(data.error || "delete_failed");
            removeMessageFromDom(message.id);
        }).catch((e) => {
            console.error("delete message failed", e);
            showStatus("Не удалось удалить сообщение");
        });
    }

    function uploadWithProgress(formData) {
        return new Promise((resolve, reject) => {
            const wrap = el("staffChatUploadProgressWrap");
            const bar = el("staffChatUploadProgressBar");
            if (wrap) wrap.classList.remove("d-none");
            if (bar) bar.style.width = "0%";
            const xhr = new XMLHttpRequest();
            xhr.open("POST", "/api/staff-chat/upload", true);
            xhr.responseType = "json";
            xhr.setRequestHeader("X-CSRFToken", document.querySelector('meta[name="csrf-token"]')?.getAttribute("content") || "");
            xhr.upload.onprogress = (evt) => {
                if (!evt.lengthComputable || !bar) return;
                const p = Math.round((evt.loaded / evt.total) * 100);
                bar.style.width = `${p}%`;
            };
            xhr.onload = () => {
                if (wrap) wrap.classList.add("d-none");
                if (xhr.status >= 200 && xhr.status < 300) {
                    resolve(xhr.response || {});
                } else {
                    reject(new Error("upload_failed"));
                }
            };
            xhr.onerror = () => {
                if (wrap) wrap.classList.add("d-none");
                reject(new Error("upload_failed"));
            };
            xhr.send(formData);
        });
    }

    function updateUnreadBadge() {
        const badge = el("staffChatFabBadge");
        if (!badge) return;
        if (state.unread > 0) {
            badge.style.display = "inline-block";
            badge.textContent = state.unread > 99 ? "99+" : String(state.unread);
        } else {
            badge.style.display = "none";
        }
    }

    function isOwnMessage(message) {
        return Number(message.user_id) === Number(window.currentUserId)
            && (message.client_instance_id || "") === state.clientInstanceId
            && (message.actor_display_name || "") === state.actorName;
    }

    function initIncomingSound() {
        try {
            const audio = new Audio("/oh-oh-icq-sound.mp3");
            audio.preload = "auto";
            state.incomingAudio = audio;
            attachAudioUnlockHandlers();
        } catch (_) {
            state.incomingAudio = null;
        }
    }

    function attachAudioUnlockHandlers() {
        const events = ["pointerdown", "keydown", "touchstart"];
        const onceUnlock = () => unlockIncomingSound();
        state.audioUnlockHandler = onceUnlock;
        events.forEach((evt) => {
            document.addEventListener(evt, onceUnlock, { passive: true });
        });
    }

    function unlockIncomingSound() {
        if (state.audioUnlocked) return;
        state.audioUnlocked = true;
        const events = ["pointerdown", "keydown", "touchstart"];
        if (state.audioUnlockHandler) {
            events.forEach((evt) => {
                document.removeEventListener(evt, state.audioUnlockHandler);
            });
            state.audioUnlockHandler = null;
        }
        if (state.pendingIncomingSound) {
            state.pendingIncomingSound = false;
            playIncomingSound();
        }
    }

    function playIncomingSound() {
        try {
            const audio = state.incomingAudio;
            if (!audio) return;
            const node = audio.cloneNode();
            node.currentTime = 0;
            node.play().catch((err) => {
                // Первый входящий звук может блокироваться браузером до жеста пользователя.
                if (err && err.name === "NotAllowedError") {
                    state.pendingIncomingSound = true;
                }
            });
        } catch (_) {
            // Беззвучно игнорируем, если браузер блокирует звук или файла нет.
        }
    }

    function showStatus(text) {
        const node = el("staffChatStatus");
        if (!node) return;
        node.textContent = text || "";
    }

    function scrollToBottom() {
        const box = el("staffChatMessages");
        if (!box) return;
        box.scrollTop = box.scrollHeight;
    }

    function formatBytes(size) {
        const value = Number(size || 0);
        if (value < 1024) return `${value} B`;
        if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
        return `${(value / (1024 * 1024)).toFixed(1)} MB`;
    }

    function formatDateTime(raw) {
        if (!raw) return "";
        let d = new Date(raw);
        if (Number.isNaN(d.getTime()) && typeof raw === "string") {
            d = new Date(raw.replace(" ", "T"));
        }
        if (Number.isNaN(d.getTime())) return String(raw);
        return d.toLocaleString("ru-RU", {
            day: "2-digit",
            month: "2-digit",
            year: "numeric",
            hour: "2-digit",
            minute: "2-digit",
        });
    }

    document.addEventListener("DOMContentLoaded", ready);
})();
