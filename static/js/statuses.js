/**
 * Управление статусами заявок
 */

let statusesList = [];
let currentEditId = null;

function toast(msg, type = 'info') {
    // Используем глобальную функцию showToast, если она есть
    if (typeof window.showToast === 'function') {
        return window.showToast(msg, type);
    }
    // Fallback: используем alert для ошибок, console.log для остального
    if (type === 'error') {
        alert(msg);
    } else {
        console.log(msg);
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text ?? '';
    return div.innerHTML;
}

// Загрузка статусов
async function loadStatuses() {
    const showArchivedEl = document.getElementById('showArchived');
    const includeArchived = showArchivedEl ? showArchivedEl.checked : false;
    
    try {
        const response = await fetch(`/api/statuses?include_archived=${includeArchived ? '1' : '0'}`);
        
        // Проверяем Content-Type
        const contentType = response.headers.get('content-type');
        if (!contentType || !contentType.includes('application/json')) {
            const text = await response.text();
            console.error('Ожидался JSON, получен:', contentType, text.substring(0, 200));
            throw new Error(`Сервер вернул не JSON (${contentType}). Возможно, требуется авторизация.`);
        }
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(`HTTP ${response.status}: ${errorData.error || response.statusText}`);
        }
        
        const data = await response.json();
        console.log('Получены данные от API:', data);
        
        if (!data) {
            throw new Error('Пустой ответ от сервера');
        }
        
        // Обрабатываем оба формата: {success: true, statuses: [...]} или просто [...]
        if (Array.isArray(data)) {
            // Если пришел массив напрямую
            statusesList = data;
            console.log(`Загружено статусов: ${statusesList.length}`);
            renderStatuses();
        } else if (data.success && Array.isArray(data.statuses)) {
            // Если пришел объект с полем statuses
            statusesList = data.statuses;
            console.log(`Загружено статусов: ${statusesList.length}`);
            renderStatuses();
        } else {
            console.error('Неверный формат ответа:', data);
            console.error('data.success:', data.success, 'Array.isArray(data.statuses):', Array.isArray(data.statuses), 'Array.isArray(data):', Array.isArray(data));
            toast('Ошибка при загрузке статусов: неверный формат ответа', 'error');
        }
    } catch (error) {
        console.error('Ошибка при загрузке статусов:', error);
        toast(`Ошибка при загрузке статусов: ${error.message}`, 'error');
    }
}

// Отображение статусов
function renderStatuses() {
    const tbody = document.getElementById('statusesTableBody');
    if (!tbody) {
        console.error('Элемент statusesTableBody не найден');
        return;
    }
    
    if (!Array.isArray(statusesList)) {
        console.error('statusesList не является массивом:', statusesList);
        tbody.innerHTML = '<tr><td colspan="6" class="text-center text-danger">Ошибка: неверный формат данных</td></tr>';
        return;
    }
    
    if (statusesList.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">Нет статусов</td></tr>';
        return;
    }
    
    tbody.innerHTML = '';
    
    statusesList.forEach(status => {
        const tr = document.createElement('tr');
        tr.dataset.statusId = status.id;
        
        const flags = [];
        if (status.is_default) flags.push('По умолчанию');
        if (status.triggers_payment_modal) flags.push('Оплата');
        if (status.accrues_salary) flags.push('Зарплата');
        if (status.is_final) flags.push('Финальный');
        if (status.blocks_edit) flags.push('Блокирует');
        if (status.requires_comment) flags.push('Комментарий');
        if (status.is_archived) flags.push('Архив');
        
        tr.innerHTML = `
            <td><i class="fas fa-grip-vertical text-muted" style="cursor: move;"></i></td>
            <td><span class="badge" style="background-color: ${status.color || '#007bff'}; width: 30px; height: 20px; display: inline-block;"></span></td>
            <td>${escapeHtml(status.name)}</td>
            <td>${escapeHtml(status.group_name || '—')}</td>
            <td>${flags.length > 0 ? flags.join(', ') : '—'}</td>
            <td>
                <button class="btn btn-sm btn-outline-primary" onclick="editStatus(${status.id})" title="Редактировать">
                    <i class="fas fa-edit"></i>
                </button>
                ${status.is_archived ? 
                    `<button class="btn btn-sm btn-outline-success" onclick="unarchiveStatus(${status.id})" title="Разархивировать">
                        <i class="fas fa-box-open"></i>
                    </button>` :
                    `<button class="btn btn-sm btn-outline-warning" onclick="archiveStatus(${status.id})" title="Архивировать">
                        <i class="fas fa-archive"></i>
                    </button>`
                }
                <button class="btn btn-sm btn-outline-danger" onclick="deleteStatus(${status.id})" title="Удалить">
                    <i class="fas fa-trash"></i>
                </button>
            </td>
        `;
        tbody.appendChild(tr);
    });
    
    // Инициализация drag-n-drop (если подключена библиотека Sortable)
    if (typeof Sortable !== 'undefined') {
        new Sortable(tbody, {
            handle: '.fa-grip-vertical',
            animation: 150,
            onEnd: function(evt) {
                const newOrder = Array.from(tbody.children).map(tr => parseInt(tr.dataset.statusId));
                reorderStatuses(newOrder);
            }
        });
    }
}

// Открытие модалки для создания
function openStatusModal() {
    currentEditId = null;
    document.getElementById('statusModalTitle').textContent = 'Добавить статус';
    document.getElementById('statusForm').reset();
    document.getElementById('statusId').value = '';
    document.getElementById('statusColor').value = '#007bff';
    const isDefEl = document.getElementById('isDefault');
    if (isDefEl) isDefEl.checked = false;
}

// Редактирование статуса
async function editStatus(statusId) {
    const status = statusesList.find(s => s.id === statusId);
    if (!status) return;
    
    currentEditId = statusId;
    document.getElementById('statusModalTitle').textContent = 'Редактировать статус';
    document.getElementById('statusId').value = status.id;
    document.getElementById('statusName').value = status.name;
    document.getElementById('statusGroup').value = status.group_name || '';
    document.getElementById('statusColor').value = status.color || '#007bff';
    document.getElementById('triggersPaymentModal').checked = status.triggers_payment_modal == 1;
    document.getElementById('accruesSalary').checked = status.accrues_salary == 1;
    document.getElementById('isFinal').checked = status.is_final == 1;
    document.getElementById('blocksEdit').checked = status.blocks_edit == 1;
    document.getElementById('isArchived').checked = status.is_archived == 1;
    const rc = document.getElementById('requiresComment');
    if (rc) rc.checked = status.requires_comment == 1;
    document.getElementById('clientName').value = status.client_name || '';
    document.getElementById('clientDescription').value = status.client_description || '';
    
    const modal = new bootstrap.Modal(document.getElementById('statusModal'));
    modal.show();
}

// Сохранение статуса
async function saveStatus() {
    const form = document.getElementById('statusForm');
    if (!form.checkValidity()) {
        form.reportValidity();
        return;
    }
    
    const data = {
        name: document.getElementById('statusName').value.trim(),
        group_name: document.getElementById('statusGroup').value,
        color: document.getElementById('statusColor').value,
        is_default: document.getElementById('isDefault')?.checked ? 1 : 0,
        triggers_payment_modal: document.getElementById('triggersPaymentModal').checked ? 1 : 0,
        accrues_salary: document.getElementById('accruesSalary').checked ? 1 : 0,
        is_final: document.getElementById('isFinal').checked ? 1 : 0,
        blocks_edit: document.getElementById('blocksEdit').checked ? 1 : 0,
        requires_comment: document.getElementById('requiresComment')?.checked ? 1 : 0,
        is_archived: document.getElementById('isArchived').checked ? 1 : 0,
        client_name: document.getElementById('clientName').value.trim() || null,
        client_description: document.getElementById('clientDescription').value.trim() || null
    };
    
    try {
        let response;
        if (currentEditId) {
            response = await fetch(`/api/statuses/${currentEditId}`, {
                method: 'PATCH',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(data)
            });
        } else {
            response = await fetch('/api/statuses', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(data)
            });
        }
        
        const result = await response.json();
        if (result.success) {
            toast('Статус сохранен', 'success');
            bootstrap.Modal.getInstance(document.getElementById('statusModal')).hide();
            loadStatuses();
        } else {
            toast(result.error || 'Ошибка при сохранении', 'error');
        }
    } catch (error) {
        console.error('Ошибка при сохранении статуса:', error);
        toast('Ошибка при сохранении статуса', 'error');
    }
}

// Архивирование статуса
async function archiveStatus(statusId) {
    if (!confirm('Архивировать статус?')) return;
    
    try {
        const response = await fetch(`/api/statuses/${statusId}/archive`, {method: 'POST'});
        const result = await response.json();
        if (result.success) {
            toast('Статус архивирован', 'success');
            loadStatuses();
        } else {
            toast(result.error || 'Ошибка', 'error');
        }
    } catch (error) {
        console.error('Ошибка при архивации:', error);
        toast('Ошибка при архивации', 'error');
    }
}

// Разархивирование статуса
async function unarchiveStatus(statusId) {
    try {
        const response = await fetch(`/api/statuses/${statusId}/unarchive`, {method: 'POST'});
        const result = await response.json();
        if (result.success) {
            toast('Статус разархивирован', 'success');
            loadStatuses();
        } else {
            toast(result.error || 'Ошибка', 'error');
        }
    } catch (error) {
        console.error('Ошибка при разархивации:', error);
        toast('Ошибка при разархивации', 'error');
    }
}

// Удаление статуса
async function deleteStatus(statusId) {
    if (!confirm('Удалить статус? Это действие нельзя отменить.')) return;
    
    try {
        const response = await fetch(`/api/statuses/${statusId}`, {method: 'DELETE'});
        const result = await response.json();
        if (result.success) {
            toast('Статус удален', 'success');
            loadStatuses();
        } else {
            toast(result.error || 'Ошибка', 'error');
        }
    } catch (error) {
        console.error('Ошибка при удалении:', error);
        toast('Ошибка при удалении', 'error');
    }
}

// Изменение порядка статусов
async function reorderStatuses(statusIds) {
    try {
        const response = await fetch('/api/statuses/reorder', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({status_ids: statusIds})
        });
        const result = await response.json();
        if (result.success) {
            toast('Порядок сохранен', 'success');
        } else {
            toast(result.error || 'Ошибка', 'error');
            loadStatuses(); // Перезагружаем при ошибке
        }
    } catch (error) {
        console.error('Ошибка при изменении порядка:', error);
        toast('Ошибка при изменении порядка', 'error');
        loadStatuses();
    }
}

// Вспомогательные функции (escapeHtml уже определена выше, удаляем дубликат)

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    loadStatuses();
});


