/* global self */
/**
 * Service Worker: входящий Web Push для чата сотрудников.
 * Регистрация: /staff-chat-push-sw.js (scope /).
 */
self.addEventListener("push", (event) => {
    let payload = {
        title: "Чат CRM",
        body: "",
        url: "/all_orders",
        icon: "/static/favicon.svg",
        tag: "staff-chat",
        data: { url: "/all_orders" },
    };
    try {
        if (event.data) {
            const j = event.data.json();
            Object.assign(payload, j);
            if (!payload.data) payload.data = {};
            if (!payload.data.url) payload.data.url = payload.url || "/all_orders";
        }
    } catch (_) {
        try {
            const t = event.data && event.data.text();
            if (t) payload.body = t.slice(0, 220);
        } catch (_) {
            /* ignore */
        }
    }
    const title = payload.title || "Чат CRM";
    const options = {
        body: payload.body || "Новое сообщение",
        icon: payload.icon || "/static/favicon.svg",
        tag: payload.tag || "staff-chat",
        data: payload.data || { url: "/all_orders" },
    };
    event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener("notificationclick", (event) => {
    event.notification.close();
    const raw = event.notification.data && event.notification.data.url;
    const url = typeof raw === "string" && raw.startsWith("/") ? raw : "/all_orders";
    event.waitUntil(
        self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((clientList) => {
            for (let i = 0; i < clientList.length; i += 1) {
                const c = clientList[i];
                if (c.url && "focus" in c) return c.focus();
            }
            if (self.clients.openWindow) {
                const abs = new URL(url, self.location.origin).href;
                return self.clients.openWindow(abs);
            }
            return undefined;
        })
    );
});
