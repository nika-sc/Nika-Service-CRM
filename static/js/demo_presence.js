/**
 * Демо: heartbeat присутствия + опрос счётчика онлайн.
 * Каждый браузер/вкладка получает свой client_instance_id (localStorage).
 */
(function () {
    "use strict";

    if (!window.demoVisitorStatsEnabled) {
        return;
    }

    var HEARTBEAT_MS = 60000;
    var POLL_MS = 30000;
    var STORAGE_KEY = "nika_demo_client_instance_id";

    function csrfToken() {
        var meta = document.querySelector('meta[name="csrf-token"]');
        return meta ? meta.getAttribute("content") || "" : "";
    }

    function uuid4() {
        if (window.crypto && typeof window.crypto.randomUUID === "function") {
            return window.crypto.randomUUID().replace(/-/g, "");
        }
        return "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx".replace(/x/g, function () {
            return ((Math.random() * 16) | 0).toString(16);
        });
    }

    function getClientInstanceId() {
        try {
            var id = localStorage.getItem(STORAGE_KEY);
            if (id && /^[A-Za-z0-9_-]{8,80}$/.test(id)) {
                return id;
            }
            id = "c_" + uuid4();
            localStorage.setItem(STORAGE_KEY, id);
            return id;
        } catch (_) {
            return "c_" + uuid4();
        }
    }

    var clientInstanceId = getClientInstanceId();
    window.demoVisitorClientInstanceId = clientInstanceId;

    // Подставляем hidden-поле в формы логина (лендинг / /login)
    function injectLoginClientId() {
        var forms = document.querySelectorAll('form[action*="login"], #demoLoginForm, form[method="POST"]');
        for (var i = 0; i < forms.length; i++) {
            var form = forms[i];
            var action = (form.getAttribute("action") || "").toLowerCase();
            if (action && action.indexOf("login") === -1 && form.id !== "demoLoginForm") {
                continue;
            }
            var existing = form.querySelector('input[name="client_instance_id"]');
            if (!existing) {
                existing = document.createElement("input");
                existing.type = "hidden";
                existing.name = "client_instance_id";
                form.appendChild(existing);
            }
            existing.value = clientInstanceId;
        }
    }
    injectLoginClientId();

    function sendHeartbeat() {
        if (!window.demoVisitorHeartbeat) {
            return;
        }
        var payload = JSON.stringify({
            path: window.location.pathname + window.location.search,
            client_instance_id: clientInstanceId,
        });
        var headers = {
            "Content-Type": "application/json",
            "X-CSRFToken": csrfToken(),
        };
        try {
            fetch("/api/demo/presence", {
                method: "POST",
                headers: headers,
                body: payload,
                credentials: "same-origin",
                keepalive: true,
            })
                .then(function (r) {
                    return r.ok ? r.json() : null;
                })
                .then(function (data) {
                    if (data && typeof data.online === "number") {
                        updateOnlineBadges(data.online);
                    }
                })
                .catch(function () {});
        } catch (_) {}
    }

    function pollOnlineCount() {
        fetch("/api/demo/online-count", { credentials: "same-origin" })
            .then(function (r) {
                return r.ok ? r.json() : null;
            })
            .then(function (data) {
                if (data && typeof data.online === "number") {
                    updateOnlineBadges(data.online);
                }
            })
            .catch(function () {});
    }

    function updateOnlineBadges(n) {
        var nodes = document.querySelectorAll("[data-demo-online-count]");
        for (var i = 0; i < nodes.length; i++) {
            nodes[i].textContent = String(n);
        }
    }

    if (window.demoVisitorHeartbeat) {
        setTimeout(sendHeartbeat, 800);
        setInterval(sendHeartbeat, HEARTBEAT_MS);
        document.addEventListener("visibilitychange", function () {
            if (document.visibilityState === "visible") {
                sendHeartbeat();
            }
        });
    }

    if (window.demoVisitorPollOnline) {
        pollOnlineCount();
        setInterval(pollOnlineCount, POLL_MS);
    }
})();
