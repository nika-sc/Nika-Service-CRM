(function () {
    function readBootConfig() {
        var el = document.getElementById('app-boot-config');
        if (!el || !el.textContent) return {};
        try {
            return JSON.parse(el.textContent);
        } catch (e) {
            return {};
        }
    }

    var cfg = readBootConfig();
    window.currentUserId = cfg.currentUserId != null ? cfg.currentUserId : null;
    window.currentUsername = cfg.currentUsername || '';
    window.currentUserRole = cfg.currentUserRole || '';
    window.staffChatEnabled = !!cfg.staffChatEnabled;
    window.staffChatPushSwUrl = cfg.staffChatPushSwUrl || '/staff-chat-push-sw.js';
    window.demoVisitorStatsEnabled = !!cfg.demoVisitorStatsEnabled;
    window.demoVisitorHeartbeat = !!cfg.demoVisitorHeartbeat;
    window.demoVisitorPollOnline = !!cfg.demoVisitorPollOnline;

    (function ensureStaffClientId() {
        var key = 'nika_staff_client_instance_id';
        var value = '';
        try {
            value = localStorage.getItem(key) || '';
            if (!value) {
                value = (window.crypto && crypto.randomUUID)
                    ? crypto.randomUUID()
                    : (String(Date.now()) + '-' + Math.random().toString(16).slice(2));
                localStorage.setItem(key, value);
            }
        } catch (e) {
            value = 'local';
        }
        window.nikaStaffClientInstanceId = value;
    })();

    if ('serviceWorker' in navigator) {
        window.addEventListener('load', function () {
            navigator.serviceWorker.register('/static/js/service-worker.js')
                .then(function (registration) {
                    console.log('Service Worker зарегистрирован:', registration.scope);
                })
                .catch(function (error) {
                    console.log('Ошибка регистрации Service Worker:', error);
                });
        });
    }
})();
