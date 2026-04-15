/**
 * Система уведомлений
 */

let notificationsSocket = null;
let unreadCount = 0;

// Инициализация системы уведомлений
document.addEventListener('DOMContentLoaded', function() {
    if (!window.currentUserId) {
        return; // Пользователь не авторизован
    }
    
    initNotifications();
    loadUnreadCount();
    setupNotificationsDropdown();
    
    // Загружаем уведомления каждые 30 секунд
    setInterval(loadUnreadCount, 30000);
});

function initNotifications() {
    // В production отключено realtime-сокет-подключение:
    // периодический REST-polling стабильнее и меньше нагружает VPS.
    notificationsSocket = null;
}

function loadUnreadCount() {
    fetch('/api/notifications/unread-count')
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                unreadCount = data.count;
                updateNotificationBadge();
            }
        })
        .catch(err => console.error('Error loading unread count:', err));
}

function updateNotificationBadge() {
    const badge = document.getElementById('notificationBadge');
    if (badge) {
        if (unreadCount > 0) {
            badge.textContent = unreadCount > 99 ? '99+' : unreadCount;
            badge.style.display = 'inline-block';
        } else {
            badge.style.display = 'none';
        }
    }
}

function setupNotificationsDropdown() {
    const btn = document.getElementById('notificationsBtn');
    const menu = document.getElementById('notificationsMenu');
    
    if (!btn || !menu) return;
    
    // Открытие/закрытие меню
    btn.addEventListener('click', function(e) {
        e.stopPropagation();
        const isVisible = menu.style.display !== 'none';
        menu.style.display = isVisible ? 'none' : 'block';
        
        if (!isVisible) {
            loadNotifications();
        }
    });
    
    // Закрытие при клике вне меню
    document.addEventListener('click', function(e) {
        if (!menu.contains(e.target) && !btn.contains(e.target)) {
            menu.style.display = 'none';
        }
    });
    
    // Кнопка "Отметить все как прочитанные"
    const markAllReadBtn = document.getElementById('markAllReadBtn');
    if (markAllReadBtn) {
        markAllReadBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            markAllAsRead();
        });
    }
}

function loadNotifications() {
    const list = document.getElementById('notificationsList');
    if (!list) return;
    
    list.innerHTML = '<div class="text-center py-3 text-muted"><i class="fas fa-spinner fa-spin"></i> Загрузка...</div>';
    
    fetch('/api/notifications?unread_only=0&limit=10')
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                renderNotifications(data.notifications);
            } else {
                list.innerHTML = '<div class="text-center py-3 text-muted">Ошибка загрузки</div>';
            }
        })
        .catch(err => {
            console.error('Error loading notifications:', err);
            list.innerHTML = '<div class="text-center py-3 text-muted">Ошибка загрузки</div>';
        });
}

function renderNotifications(notifications) {
    const list = document.getElementById('notificationsList');
    const markAllReadBtn = document.getElementById('markAllReadBtn');
    
    if (!list) return;
    
    if (notifications.length === 0) {
        list.innerHTML = '<div class="text-center py-3 text-muted">Нет уведомлений</div>';
        if (markAllReadBtn) markAllReadBtn.style.display = 'none';
        return;
    }
    
    // Показываем кнопку "Отметить все", если есть непрочитанные
    const hasUnread = notifications.some(n => !n.read_at);
    if (markAllReadBtn) {
        markAllReadBtn.style.display = hasUnread ? 'block' : 'none';
    }
    
    list.innerHTML = notifications.map(notif => {
        const isRead = notif.read_at !== null;
        const timeAgo = formatTimeAgo(notif.created_at);
        const entityLink = notif.entity_type && notif.entity_id 
            ? getEntityLink(notif.entity_type, notif.entity_id)
            : '';
        
        return `
            <div class="notification-item ${isRead ? '' : 'unread'}" data-notification-id="${notif.id}">
                <div class="notification-content">
                    <div class="notification-title">${escapeHtml(notif.title)}</div>
                    <div class="notification-message">${escapeHtml(notif.message)}</div>
                    <div class="notification-meta">
                        <small class="text-muted">${timeAgo}</small>
                        ${entityLink ? `<a href="${entityLink}" class="notification-link">Открыть</a>` : ''}
                    </div>
                </div>
                ${!isRead ? '<button class="btn btn-sm btn-link mark-read-btn" data-id="' + notif.id + '"><i class="fas fa-check"></i></button>' : ''}
            </div>
        `;
    }).join('');
    
    // Обработчики для кнопок "Отметить как прочитанное"
    list.querySelectorAll('.mark-read-btn').forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.stopPropagation();
            const notificationId = parseInt(this.dataset.id);
            markAsRead(notificationId);
        });
    });
}

function markAsRead(notificationId) {
    fetch(`/api/notifications/${notificationId}/read`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || ''
        }
    })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                loadUnreadCount();
                loadNotifications();
            }
        })
        .catch(err => console.error('Error marking notification as read:', err));
}

function markAllAsRead() {
    fetch('/api/notifications/read-all', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || ''
        }
    })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                unreadCount = 0;
                updateNotificationBadge();
                loadNotifications();
            }
        })
        .catch(err => console.error('Error marking all as read:', err));
}

function showNotificationToast(notification) {
    // Используем существующую систему toast, если есть
    if (typeof showToast === 'function') {
        showToast(notification.message, 'info');
    } else {
        // Простое уведомление
        const toast = document.createElement('div');
        toast.className = 'notification-toast';
        toast.innerHTML = `
            <div class="notification-toast-content">
                <strong>${escapeHtml(notification.title)}</strong>
                <p>${escapeHtml(notification.message)}</p>
            </div>
        `;
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.classList.add('show');
        }, 10);
        
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        }, 5000);
    }
}

function formatTimeAgo(dateString) {
    if (!dateString) return '';

    let date = new Date(dateString);
    if (isNaN(date.getTime()) && typeof dateString === 'string') {
        // Fallback для старого формата из SQLite: "YYYY-MM-DD HH:MM:SS"
        const normalized = dateString.includes('T') ? dateString : dateString.replace(' ', 'T');
        date = new Date(normalized);
    }
    if (isNaN(date.getTime())) return '';

    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);
    
    if (diffMins < 1) return 'только что';
    if (diffMins < 60) return `${diffMins} мин. назад`;
    if (diffHours < 24) return `${diffHours} ч. назад`;
    if (diffDays < 7) return `${diffDays} дн. назад`;
    
    return date.toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' });
}

function getEntityLink(entityType, entityId) {
    const links = {
        'order': `/order/${entityId}`,
        'customer': `/clients/${entityId}`,
        'part': `/warehouse/parts/${entityId}`
    };
    return links[entityType] || '';
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
