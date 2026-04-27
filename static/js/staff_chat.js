(() => {
    const ROOM_KEY = "global";
    const NS = "/staff-chat";
    const ALWAYS_OPEN = false;
    const START_OPEN = true;
    const STORAGE_ACTOR = `staff_chat_actor_${window.currentUserId || "anon"}`;
    const STORAGE_CLIENT = `staff_chat_client_${window.currentUserId || "anon"}`;
    const STORAGE_PANEL_OPEN = `staff_chat_open_${window.currentUserId || "anon"}`;
    const STORAGE_BROWSER_NOTIFY = `staff_chat_browser_notify_${window.currentUserId || "anon"}`;
    const STORAGE_WEB_PUSH = `staff_chat_webpush_${window.currentUserId || "anon"}`;
    /** Иконка в системном уведомлении (как на вкладке). */
    const STAFF_CHAT_NOTIFY_ICON = "/static/favicon.svg";
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
            maxMessageLength: 4000,
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
        /** Базовый заголовок вкладки (без префикса чата) */
        docTitleBase: null,
        /** Сколько входящих от других пришло, пока пользователь не на вкладке */
        titleIncomingCount: 0,
        titleBlinkTimer: null,
        titleBlinkShowAlert: true,
        readCursorTimer: null,
        readReceiptsRefreshTimer: null,
        browserNotifyEnabled: false,
    };

    function ready() {
        if (!window.currentUserId || !window.staffChatEnabled) return;
        bindElements();
        restoreIdentity();
        initIncomingSound();
        initSocket();
        initDocumentTitleAlerts();
        initBrowserNotificationsUi();
        setPanelOpen(restorePanelState());
        loadHistory();
        startPeriodicSync();
        void initWebPushUi();
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
        const notifyBtn = el("staffChatNotifyBtn");
        if (notifyBtn) {
            notifyBtn.addEventListener("click", (e) => {
                if (e.shiftKey) {
                    e.preventDefault();
                    testBrowserNotificationFromBell();
                    return;
                }
                onBrowserNotifyButtonClick();
            });
        }
        const webPushBtn = el("staffChatWebPushBtn");
        if (webPushBtn) {
            webPushBtn.addEventListener("click", () => {
                onWebPushButtonClick().catch((err) => console.error("web push", err));
            });
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
            if (userAttentionOnPage()) {
                clearChatTitleNotification();
            }
            scrollToBottom();
            scheduleReadCursorPost();
            postReadCursorSoon();
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
        socket.on("read_cursor_updated", (payload) => {
            if (!payload || payload.room_key !== ROOM_KEY) return;
            const sameReader =
                Number(payload.user_id) === Number(window.currentUserId) &&
                (payload.client_instance_id || "") === (state.clientInstanceId || "");
            if (sameReader) return;
            scheduleReadReceiptsRefresh();
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
            const hadOpenAtStart = state.isOpen;
            sorted.forEach((m) => {
                if (!m || !m.id) return;
                if (!state.newestId || Number(m.id) > Number(state.newestId)) {
                    appendMessage(m, true, hadOpenAtStart);
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
            applyChatLimitsFromApi(data.limits);
            if (!messages.length) {
                if (!beforeId) {
                    scheduleReadCursorPost();
                    postReadCursorSoon();
                }
                return;
            }
            prependMessages(messages, !!beforeId);
            if (!beforeId) {
                scheduleReadCursorPost();
                postReadCursorSoon();
            }
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

    function appendMessage(message, fromSocket, hadPanelOpenOverride) {
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
                const hadPanelOpen =
                    typeof hadPanelOpenOverride === "boolean" ? hadPanelOpenOverride : state.isOpen;
                playIncomingSound();
                if (!state.isOpen) {
                    setPanelOpen(true);
                }
                alertDocumentTitleForIncomingChat(hadPanelOpen);
                maybeBrowserNotify(message, hadPanelOpen);
            }
        }

        if (state.isOpen) {
            scrollToBottom();
            scheduleReadCursorPost();
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

    function createReadReceiptsNode(message) {
        if (!message.read_receipts || Number(message.read_receipts.count) <= 0) return null;
        const rr = document.createElement("div");
        rr.className = "staff-chat-read-receipts";
        const sample = Array.isArray(message.read_receipts.sample) ? message.read_receipts.sample : [];
        const cnt = Number(message.read_receipts.count) || 0;
        rr.appendChild(document.createTextNode(`Прочитали: ${sample.join(", ")}`));
        const extra = cnt - sample.length;
        if (extra > 0) {
            const more = document.createElement("button");
            more.type = "button";
            more.className = "staff-chat-read-receipts-more";
            more.textContent = `+${extra}`;
            more.title = "Показать всех";
            more.addEventListener("click", () => showAllReaders(message.id));
            rr.appendChild(more);
        }
        return rr;
    }

    function setReadReceiptsOnMessageNode(messageEl, message) {
        const existing = messageEl.querySelector(".staff-chat-read-receipts");
        if (existing) existing.remove();
        const rr = createReadReceiptsNode(message);
        if (!rr) return;
        const reactionsRow = messageEl.querySelector(".staff-chat-reactions");
        if (reactionsRow && reactionsRow.parentNode === messageEl) {
            messageEl.insertBefore(rr, reactionsRow);
        } else {
            messageEl.appendChild(rr);
        }
    }

    function buildMessageNode(message, trustServerOwnFlags = true) {
        const item = document.createElement("div");
        item.className = "staff-chat-message";
        item.dataset.messageId = String(message.id);
        const mine = isOwnMessage(message);
        if (mine) item.classList.add("mine");

        const head = document.createElement("div");
        head.className = "staff-chat-message-head";

        const authorEl = document.createElement("span");
        authorEl.className = "staff-chat-author";
        authorEl.textContent = message.actor_display_name || message.username || "Сотрудник";
        head.appendChild(authorEl);

        const sepAfterAuthor = document.createElement("span");
        sepAfterAuthor.className = "staff-chat-head-sep";
        sepAfterAuthor.textContent = "·";
        sepAfterAuthor.setAttribute("aria-hidden", "true");
        head.appendChild(sepAfterAuthor);

        const via = message.username ? `через ${message.username}` : "";
        const metaEl = document.createElement("span");
        metaEl.className = "staff-chat-meta";
        metaEl.textContent = `${formatDateTime(message.created_at)}${via ? ` · ${via}` : ""}`;
        head.appendChild(metaEl);

        if (message.edited_at) {
            const sepEdited = document.createElement("span");
            sepEdited.className = "staff-chat-head-sep";
            sepEdited.textContent = "·";
            sepEdited.setAttribute("aria-hidden", "true");
            head.appendChild(sepEdited);
            const editedEl = document.createElement("span");
            editedEl.className = "staff-chat-edited-flag";
            editedEl.textContent = "изм.";
            editedEl.title = "Сообщение изменено";
            head.appendChild(editedEl);
        }

        if (mine) {
            const spacer = document.createElement("span");
            spacer.className = "staff-chat-head-spacer";
            spacer.setAttribute("aria-hidden", "true");
            head.appendChild(spacer);

            const actions = document.createElement("span");
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
            head.appendChild(actions);
        }

        item.appendChild(head);

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

        const rrEl = createReadReceiptsNode(message);
        if (rrEl) item.appendChild(rrEl);

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

    function userAttentionOnPage() {
        if (document.hidden) return false;
        if (typeof document.hasFocus === "function" && !document.hasFocus()) return false;
        return true;
    }

    /** Вкладка в фокусе и панель чата уже была открыта — звук есть, desktop-уведомление и заголовок вкладки не нужны. */
    function userLikelyViewingOpenChat(hadPanelOpenWhenMessageArrived) {
        if (!hadPanelOpenWhenMessageArrived) return false;
        if (document.hidden) return false;
        if (typeof document.hasFocus === "function" && !document.hasFocus()) return false;
        return true;
    }

    function ensureDocTitleBase() {
        if (!state.docTitleBase) {
            state.docTitleBase = document.title;
        }
    }

    function buildChatAlertTitle() {
        const base = state.docTitleBase || "";
        const n = state.titleIncomingCount;
        const prefix = n > 1 ? `(${n}) ` : "";
        return `${prefix}💬 Новое сообщение — ${base}`;
    }

    function stopTitleBlinkTimer() {
        if (state.titleBlinkTimer) {
            clearInterval(state.titleBlinkTimer);
            state.titleBlinkTimer = null;
        }
    }

    function onTitleBlinkTick() {
        if (state.titleIncomingCount < 1 || !state.docTitleBase) {
            stopTitleBlinkTimer();
            if (state.docTitleBase) document.title = state.docTitleBase;
            return;
        }
        if (!document.hidden) {
            stopTitleBlinkTimer();
            document.title = buildChatAlertTitle();
            return;
        }
        state.titleBlinkShowAlert = !state.titleBlinkShowAlert;
        document.title = state.titleBlinkShowAlert ? buildChatAlertTitle() : state.docTitleBase;
    }

    function startTitleBlinkTimer() {
        if (!document.hidden || state.titleIncomingCount < 1 || !state.docTitleBase) return;
        stopTitleBlinkTimer();
        state.titleBlinkShowAlert = true;
        document.title = buildChatAlertTitle();
        state.titleBlinkTimer = setInterval(onTitleBlinkTick, 1100);
    }

    function alertDocumentTitleForIncomingChat(hadPanelOpenWhenMessageArrived) {
        if (userLikelyViewingOpenChat(hadPanelOpenWhenMessageArrived)) return;
        ensureDocTitleBase();
        state.titleIncomingCount += 1;
        if (document.hidden) {
            startTitleBlinkTimer();
        } else {
            stopTitleBlinkTimer();
            document.title = buildChatAlertTitle();
        }
    }

    function clearChatTitleNotification() {
        stopTitleBlinkTimer();
        state.titleIncomingCount = 0;
        state.titleBlinkShowAlert = true;
        if (state.docTitleBase) document.title = state.docTitleBase;
    }

    function initDocumentTitleAlerts() {
        state.docTitleBase = document.title;
        document.addEventListener("visibilitychange", () => {
            if (document.visibilityState === "visible") {
                clearChatTitleNotification();
            } else if (state.titleIncomingCount > 0) {
                startTitleBlinkTimer();
            }
        });
        window.addEventListener("focus", () => {
            clearChatTitleNotification();
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

    function applyChatLimitsFromApi(limits) {
        if (!limits) return;
        const maxFiles = Number(limits.max_files_per_message || state.limits.maxFiles);
        const maxFileSizeBytes = Number(limits.max_file_size_bytes || (state.limits.maxFileSizeMb * 1024 * 1024));
        state.limits.maxFiles = maxFiles;
        state.limits.maxFileSizeMb = Math.max(1, Math.round(maxFileSizeBytes / (1024 * 1024)));
        if (limits.max_message_length) {
            state.limits.maxMessageLength = Math.max(1, Number(limits.max_message_length));
            const ta = el("staffChatInput");
            if (ta) ta.maxLength = state.limits.maxMessageLength;
        }
        const hint = el("staffChatLimitsHint");
        if (hint) {
            const rpm = limits.max_messages_per_minute != null ? `, не более ${limits.max_messages_per_minute} сообщ./мин` : "";
            hint.textContent = `Лимиты: до ${state.limits.maxFiles} файлов, до ${state.limits.maxFileSizeMb} MB, до ${state.limits.maxMessageLength} симв.${rpm}`;
        }
    }

    function getStaffChatCsrfToken() {
        return document.querySelector('meta[name="csrf-token"]')?.getAttribute("content") || "";
    }

    function scheduleReadCursorPost() {
        if (!state.isOpen) return;
        clearTimeout(state.readCursorTimer);
        state.readCursorTimer = setTimeout(postReadCursorNow, 900);
    }

    function postReadCursorSoon() {
        if (!state.isOpen || !state.newestId) return;
        setTimeout(() => postReadCursorNow(), 160);
    }

    function postReadCursorNow() {
        if (!state.newestId || !state.isOpen) return;
        const id = Number(state.newestId);
        fetch("/api/staff-chat/read-cursor", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": getStaffChatCsrfToken(),
            },
            body: JSON.stringify({
                room_key: ROOM_KEY,
                last_read_message_id: id,
                actor_display_name: state.actorName,
                client_instance_id: state.clientInstanceId,
            }),
            credentials: "same-origin",
        }).catch(() => {});
    }

    function scheduleReadReceiptsRefresh() {
        clearTimeout(state.readReceiptsRefreshTimer);
        state.readReceiptsRefreshTimer = setTimeout(() => {
            state.readReceiptsRefreshTimer = null;
            refreshReadReceiptsFromServer();
        }, 320);
    }

    async function refreshReadReceiptsFromServer() {
        try {
            const query = new URLSearchParams();
            query.set("limit", String(MAX_HISTORY_LIMIT));
            query.set("room_key", ROOM_KEY);
            query.set("actor_display_name", state.actorName || "");
            query.set("client_instance_id", state.clientInstanceId || "");
            const resp = await fetch(`/api/staff-chat/history?${query.toString()}`, { credentials: "same-origin" });
            const data = await resp.json();
            if (!data || !data.success || !Array.isArray(data.messages)) return;
            data.messages.forEach((m) => {
                if (!m || !m.id) return;
                const node = document.querySelector(`.staff-chat-message[data-message-id="${String(m.id)}"]`);
                if (!node) return;
                setReadReceiptsOnMessageNode(node, m);
            });
        } catch (_) {
            // тихо: не мешаем работе чата
        }
    }

    function showAllReaders(messageId) {
        const params = new URLSearchParams({ room_key: ROOM_KEY });
        fetch(`/api/staff-chat/message/${messageId}/readers?${params.toString()}`, { credentials: "same-origin" })
            .then((r) => r.json())
            .then((data) => {
                if (!data.success) {
                    showStatus(data.error || "Не удалось загрузить список");
                    return;
                }
                const readers = Array.isArray(data.readers) ? data.readers : [];
                if (!readers.length) {
                    window.alert("Пока никто не отметил прочтение до этого сообщения (или миграция БД не применена).");
                    return;
                }
                const lines = readers.map((x) => {
                    const u = (x.username || "").trim();
                    const lab = (x.label || "").trim() || u || "—";
                    const extra = u && u !== lab ? ` (${u})` : "";
                    return `${lab}${extra} — прочитано до №${x.last_read_message_id}`;
                });
                window.alert(`Прочитали сообщение №${messageId}:\n\n${lines.join("\n")}`);
            })
            .catch(() => showStatus("Не удалось загрузить список"));
    }

    /**
     * Показ системного уведомления (не Web Push). Возвращает причину при ошибке —
     * раньше ошибки глотались в try/catch, из‑за этого казалось, что «ничего не работает».
     */
    function tryShowBrowserNotification(title, body, extraOpts) {
        if (typeof Notification === "undefined") {
            return { ok: false, message: "Notification API недоступен в этом браузере" };
        }
        if (Notification.permission !== "granted") {
            return {
                ok: false,
                message: `Нет разрешения (${Notification.permission}). Нажмите 🔔 и разрешите сайту уведомления.`,
            };
        }
        const opts = Object.assign(
            {
                body: body || "",
                icon: STAFF_CHAT_NOTIFY_ICON,
            },
            extraOpts || {}
        );
        try {
            const n = new Notification(title || "CRM", opts);
            n.onerror = () => {
                console.warn("staff_chat: Notification.onerror (см. настройки ОС / Chrome для этого сайта)");
            };
            return { ok: true };
        } catch (err) {
            const msg = err && err.message ? err.message : String(err);
            return { ok: false, message: msg };
        }
    }

    function runBellNotificationSelfTest() {
        const r = tryShowBrowserNotification(
            "Чат CRM — тест",
            "Если баннера нет: откройте Центр уведомлений (Win+N). Проверьте Focus Assist и разрешения для Chrome.",
            { tag: "staff-chat-self-test", requireInteraction: false }
        );
        if (!r.ok) {
            showStatus(r.message || "Не удалось показать уведомление");
            return;
        }
        showStatus("Тест отправлен в ОС. Смотрите баннер или Win+N (Центр уведомлений).");
    }

    function testBrowserNotificationFromBell() {
        if (typeof Notification === "undefined") {
            showStatus("Браузер не поддерживает Notification API");
            return;
        }
        if (Notification.permission === "denied") {
            showStatus(
                "Сайт в списке «Блокировать» для уведомлений. В Chrome: замок слева от адреса → Уведомления → Разрешить."
            );
            return;
        }
        if (Notification.permission === "default") {
            Notification.requestPermission().then((p) => {
                refreshNotifyButton();
                if (p !== "granted") {
                    showStatus(`Разрешение не выдано: ${p}`);
                    return;
                }
                runBellNotificationSelfTest();
            });
            return;
        }
        runBellNotificationSelfTest();
    }

    function initBrowserNotificationsUi() {
        try {
            state.browserNotifyEnabled = localStorage.getItem(STORAGE_BROWSER_NOTIFY) === "1";
        } catch (_) {
            state.browserNotifyEnabled = false;
        }
        refreshNotifyButton();
    }

    function refreshNotifyButton() {
        const btn = el("staffChatNotifyBtn");
        if (!btn) return;
        const hasApi = typeof Notification !== "undefined";
        const perm = hasApi ? Notification.permission : "denied";
        const on = state.browserNotifyEnabled && perm === "granted";
        btn.classList.toggle("is-active", on);
        const hint = " Shift+клик — проверка баннера.";
        if (!hasApi) {
            btn.title = "Браузер не поддерживает уведомления";
        } else if (perm === "denied") {
            btn.title = "Уведомления запрещены для сайта в браузере." + hint;
        } else if (perm === "default") {
            btn.title = "Включить уведомления (клик → разрешить запрос браузера)." + hint;
        } else {
            btn.title = on
                ? "Уведомления включены (клик — выключить)." + hint
                : "Включить показ уведомлений о новых сообщениях." + hint;
        }
    }

    function onBrowserNotifyButtonClick() {
        if (typeof Notification === "undefined") {
            showStatus("Браузер не поддерживает Notification API");
            return;
        }
        if (Notification.permission === "denied") {
            showStatus("Разрешите уведомления в настройках сайта в браузере");
            return;
        }
        if (Notification.permission === "default") {
            Notification.requestPermission().then((p) => {
                if (p === "granted") {
                    state.browserNotifyEnabled = true;
                    try {
                        localStorage.setItem(STORAGE_BROWSER_NOTIFY, "1");
                    } catch (_) {}
                    const test = tryShowBrowserNotification("Чат сотрудников", "Уведомления включены", {
                        tag: "staff-chat-enabled",
                    });
                    if (!test.ok) {
                        showStatus(test.message || "Разрешение есть, но показ не удался");
                    }
                }
                refreshNotifyButton();
            });
            return;
        }
        state.browserNotifyEnabled = !state.browserNotifyEnabled;
        try {
            localStorage.setItem(STORAGE_BROWSER_NOTIFY, state.browserNotifyEnabled ? "1" : "0");
        } catch (_) {}
        refreshNotifyButton();
    }

    function maybeBrowserNotify(message, hadPanelOpenWhenMessageArrived) {
        if (!state.browserNotifyEnabled || typeof Notification === "undefined") return;
        if (Notification.permission !== "granted") return;
        if (userLikelyViewingOpenChat(hadPanelOpenWhenMessageArrived)) return;
        const title = message.actor_display_name || message.username || "Чат";
        let body = (message.message_text || "").replace(/\s+/g, " ").trim();
        const atts = Array.isArray(message.attachments) ? message.attachments : [];
        if (!body && atts.length) {
            body = `Вложение: ${atts[0].original_name || "файл"}`;
        }
        if (!body) body = "Новое сообщение";
        body = body.slice(0, 200);
        const r = tryShowBrowserNotification(title, body, { tag: `staff-chat-${message.id}` });
        if (!r.ok && r.message) {
            console.warn("staff_chat: входящее уведомление:", r.message);
        }
    }

    function staffChatPushContextOk() {
        if (location.protocol === "https:") return true;
        const h = location.hostname;
        return h === "localhost" || h === "127.0.0.1";
    }

    function urlBase64ToUint8Array(base64String) {
        const s = (base64String || "").trim();
        const padding = "=".repeat((4 - (s.length % 4)) % 4);
        const base64 = (s + padding).replace(/-/g, "+").replace(/_/g, "/");
        const raw = atob(base64);
        const out = new Uint8Array(raw.length);
        for (let i = 0; i < raw.length; i += 1) out[i] = raw.charCodeAt(i);
        return out;
    }

    async function initWebPushUi() {
        const btn = el("staffChatWebPushBtn");
        if (!btn || !("serviceWorker" in navigator) || !("PushManager" in window)) {
            if (btn) btn.classList.add("d-none");
            return;
        }
        if (!staffChatPushContextOk()) {
            btn.classList.add("d-none");
            return;
        }
        try {
            const resp = await fetch("/api/staff-chat/push/config", { credentials: "same-origin" });
            const data = await resp.json();
            if (!data || !data.success || !data.ready || !data.public_key) {
                btn.classList.add("d-none");
                return;
            }
            btn.dataset.vapidPublicKey = data.public_key;
            btn.classList.remove("d-none");
        } catch (_) {
            btn.classList.add("d-none");
            return;
        }
        refreshWebPushButton();
    }

    function refreshWebPushButton() {
        const btn = el("staffChatWebPushBtn");
        if (!btn || btn.classList.contains("d-none")) return;
        let on = false;
        try {
            on = localStorage.getItem(STORAGE_WEB_PUSH) === "1";
        } catch (_) {
            on = false;
        }
        btn.classList.toggle("is-active", on);
        btn.title = on
            ? "Web Push включён (клик — отключить). Уведомления при закрытой вкладке."
            : "Web Push — включить уведомления при закрытой вкладке (сервер: VAPID + pywebpush).";
    }

    async function getStaffChatPushRegistration() {
        const path = (window.staffChatPushSwUrl || "/staff-chat-push-sw.js").replace(/^\/?/, "/");
        const reg = await navigator.serviceWorker.register(path, { scope: "/" });
        try {
            await reg.update();
        } catch (_) {
            /* ignore */
        }
        return reg;
    }

    async function onWebPushButtonClick() {
        const btn = el("staffChatWebPushBtn");
        if (!btn || btn.classList.contains("d-none")) return;
        const pubB64 = btn.dataset.vapidPublicKey;
        if (!pubB64) {
            showStatus("Web Push на сервере не настроен");
            return;
        }
        let enabled = false;
        try {
            enabled = localStorage.getItem(STORAGE_WEB_PUSH) === "1";
        } catch (_) {
            enabled = false;
        }
        if (enabled) {
            try {
                const reg = await getStaffChatPushRegistration();
                const sub = await reg.pushManager.getSubscription();
                if (sub) {
                    const ep = sub.endpoint;
                    await sub.unsubscribe();
                    await fetch("/api/staff-chat/push/unsubscribe", {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json",
                            "X-CSRFToken": getStaffChatCsrfToken(),
                        },
                        body: JSON.stringify({ endpoint: ep }),
                        credentials: "same-origin",
                    });
                }
                try {
                    localStorage.removeItem(STORAGE_WEB_PUSH);
                } catch (_) {}
                refreshWebPushButton();
                showStatus("Web Push отключён");
            } catch (e) {
                showStatus("Не удалось отключить Web Push");
            }
            return;
        }
        if (typeof Notification === "undefined") {
            showStatus("Нужен Notification API для Web Push");
            return;
        }
        if (Notification.permission === "denied") {
            showStatus("Разрешите уведомления для сайта в настройках браузера");
            return;
        }
        if (Notification.permission === "default") {
            const p = await Notification.requestPermission();
            if (p !== "granted") {
                showStatus("Без разрешения Web Push недоступен");
                return;
            }
        }
        try {
            const reg = await getStaffChatPushRegistration();
            const key = urlBase64ToUint8Array(pubB64);
            let sub = await reg.pushManager.getSubscription();
            if (!sub) {
                sub = await reg.pushManager.subscribe({
                    userVisibleOnly: true,
                    applicationServerKey: key,
                });
            }
            const resp = await fetch("/api/staff-chat/push/subscribe", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": getStaffChatCsrfToken(),
                },
                body: JSON.stringify({ subscription: sub.toJSON() }),
                credentials: "same-origin",
            });
            const data = await resp.json();
            if (!data || !data.success) {
                showStatus((data && data.error) || "Не удалось сохранить подписку");
                return;
            }
            try {
                localStorage.setItem(STORAGE_WEB_PUSH, "1");
            } catch (_) {}
            refreshWebPushButton();
            showStatus("Web Push включён — закройте вкладку и попросите коллегу написать в чат");
        } catch (e) {
            showStatus("Ошибка Web Push (HTTPS или localhost, разрешение браузера)");
        }
    }

    document.addEventListener("DOMContentLoaded", ready);
})();
