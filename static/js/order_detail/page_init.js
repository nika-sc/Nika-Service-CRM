/* Extracted from templates/order_detail.html — keep in sync with NIKA_ORDER_PAGE bootstrap. */
// ===== КОНСТАНТЫ =====
        const ORDER_ID = window.NIKA_ORDER_PAGE.orderId;
        window.ORDER_ID = ORDER_ID;

        document.addEventListener('DOMContentLoaded', function() {
            // Блокировка редактирования при загрузке страницы (если статус блокирует редактирование)
            if (window.NIKA_ORDER_PAGE && window.NIKA_ORDER_PAGE.blocksEdit) {
            const blockedMsg = 'Сначала откройте заявку';
            const editButton = document.getElementById('editOrderBtn') || document.querySelector('[data-bs-target="#editOrderModal"]');
            if (editButton) {
                editButton.style.opacity = '0.5';
                editButton.style.cursor = 'not-allowed';
                editButton.title = 'Сначала откройте заявку';
                editButton.setAttribute('aria-disabled', 'true');
                editButton.removeAttribute('data-bs-toggle');
                editButton.removeAttribute('data-bs-target');
                editButton.addEventListener('click', function(e) {
                    e.preventDefault();
                    e.stopImmediatePropagation();
                    showToast(blockedMsg, 'warning', 'Заявка закрыта');
                    return false;
                }, true);
            }
            // Кнопка «Добавить» (услуги/товары)
            const addItemsBtn = document.getElementById('openAddItemsModalBtn');
            if (addItemsBtn) {
                addItemsBtn.style.opacity = '0.5';
                addItemsBtn.style.cursor = 'not-allowed';
                addItemsBtn.title = blockedMsg;
                addItemsBtn.setAttribute('aria-disabled', 'true');
                addItemsBtn.removeAttribute('data-bs-toggle');
                addItemsBtn.removeAttribute('data-bs-target');
                addItemsBtn.addEventListener('click', function(e) {
                    e.preventDefault();
                    e.stopImmediatePropagation();
                    showToast(blockedMsg, 'warning', 'Заявка закрыта');
                    return false;
                }, true);
            }
            // Кнопка «Добавить оплату»
            const addPaymentBtn = document.getElementById('addPaymentBtn');
            if (addPaymentBtn) {
                addPaymentBtn.style.opacity = '0.5';
                addPaymentBtn.style.cursor = 'not-allowed';
                addPaymentBtn.title = blockedMsg;
                addPaymentBtn.setAttribute('aria-disabled', 'true');
                addPaymentBtn.removeAttribute('data-bs-toggle');
                addPaymentBtn.removeAttribute('data-bs-target');
                addPaymentBtn.addEventListener('click', function(e) {
                    e.preventDefault();
                    e.stopImmediatePropagation();
                    showToast(blockedMsg, 'warning', 'Заявка закрыта');
                    return false;
                }, true);
            }
            // Обработчик show.bs.modal для addItemsModal — защита от программного открытия
            const addItemsModal = document.getElementById('addItemsModal');
            if (addItemsModal) {
                addItemsModal.addEventListener('show.bs.modal', function(e) {
                    e.preventDefault();
                    e.stopPropagation();
                    showToast(blockedMsg, 'warning', 'Заявка закрыта');
                    return false;
                }, true);
            }
            // Аналогично для addPaymentModal — при закрытой заявке блокируем, кроме вызова из openPaymentModalWithDebt
            const addPaymentModalEl = document.getElementById('addPaymentModal');
            if (addPaymentModalEl) {
                addPaymentModalEl.addEventListener('show.bs.modal', function(e) {
                    if (!window._paymentModalFromCloseFlow) {
                        e.preventDefault();
                        e.stopPropagation();
                        showToast(blockedMsg, 'warning', 'Заявка закрыта');
                        return false;
                    }
                    window._paymentModalFromCloseFlow = false;
                }, true);
            }
            }
        });
        const MODAL_INIT_DELAY = 100;
        const SEARCH_DEBOUNCE_DELAY = 300;
        const TOAST_DURATION = 4000;
        const RELOAD_DELAY = 500;
        
        // ===== УТИЛИТА ДЛЯ ИНИЦИАЛИЗАЦИИ ПОСЛЕ ЗАГРУЗКИ DOM =====
        // Выполняет функцию после загрузки DOM, даже если DOM уже загружен
        function whenDOMReady(callback) {
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', callback);
            } else {
                // DOM уже загружен, выполняем сразу
                callback();
            }
        }

        // ===== ИДЕМПОТЕНТНОСТЬ ДЛЯ ОПЛАТ (защита от двойного клика) =====
        function generateIdempotencyKey() {
            if (window.crypto && typeof window.crypto.randomUUID === 'function') {
                return window.crypto.randomUUID();
            }
            return 'idem_' + Date.now() + '_' + Math.random().toString(16).slice(2);
        }

        // copyToClipboard уже определена в начале файла в блоке styles
        
        // ===== СИСТЕМА УВЕДОМЛЕНИЙ (TOAST) =====
        /**
         * Показывает toast-уведомление
         * @param {string} message - Текст сообщения
         * @param {string} type - Тип уведомления: 'success', 'error', 'warning', 'info'
         * @param {string} title - Заголовок (опционально)
         * @param {number} duration - Длительность отображения в мс (по умолчанию TOAST_DURATION)
         * @returns {HTMLElement} - Элемент toast для дальнейшего управления
         */
        // Делаем showToast глобально доступной
        window.showToast = function(message, type = 'info', title = null, duration = TOAST_DURATION) {
            // Создаем контейнер, если его нет
            let container = document.getElementById('toastContainer');
            if (!container) {
                container = document.createElement('div');
                container.id = 'toastContainer';
                container.className = 'toast-container';
                document.body.appendChild(container);
            }
            
            // Создаем уведомление
            const toast = document.createElement('div');
            toast.className = `toast-notification ${type}`;
            
            const icons = {
                success: 'fa-check-circle',
                error: 'fa-exclamation-circle',
                warning: 'fa-exclamation-triangle',
                info: 'fa-info-circle'
            };
            
            const titlesDefault = {
                success: 'Успешно',
                error: 'Ошибка',
                warning: 'Внимание',
                info: 'Информация'
            };
            
            // Безопасное создание toast уведомления
            const icon = DOMUtils.createElement('i', '', {
                'class': `fas ${icons[type] || icons.info} toast-icon`
            });
            
            const content = DOMUtils.createElement('div', '', {'class': 'toast-content'});
            
            if (title) {
                const titleEl = DOMUtils.createElement('div', title, {'class': 'toast-title'});
                content.appendChild(titleEl);
            }
            
            const messageEl = DOMUtils.createElement('div', message, {'class': 'toast-message'});
            content.appendChild(messageEl);
            
            const closeBtn = DOMUtils.createElement('button', '', {
                'class': 'toast-close',
                'aria-label': 'Закрыть'
            });
            const closeIcon = DOMUtils.createElement('i', '', {'class': 'fas fa-times'});
            closeBtn.appendChild(closeIcon);
            
            toast.appendChild(icon);
            toast.appendChild(content);
            toast.appendChild(closeBtn);
            
            container.appendChild(toast);
            
            // Обработчик закрытия (используем уже созданную кнопку)
            const closeToast = () => {
                toast.classList.add('hiding');
                setTimeout(() => {
                    if (toast.parentNode) {
                        toast.parentNode.removeChild(toast);
                    }
                }, 300);
            };
            
            closeBtn.addEventListener('click', closeToast);
            
            // Автоматическое закрытие
            if (duration > 0) {
                setTimeout(closeToast, duration);
            }
            
            return toast;
        }
        
        // ===== УТИЛИТЫ ДЛЯ API ЗАПРОСОВ =====
        /**
         * Универсальная функция для добавления услуги или товара в заявку
         * @param {string} type - Тип: 'service' или 'part'
         * @param {number} itemId - ID услуги или товара
         * @param {number} quantity - Количество
         * @param {number|null} price - Цена (опционально)
         * @returns {Promise<Object>} - Результат операции
         */
        function pageOrderId() {
            const raw = (window.NIKA_ORDER_PAGE && window.NIKA_ORDER_PAGE.orderId) || window.ORDER_ID;
            const id = parseInt(raw, 10);
            return Number.isFinite(id) && id > 0 ? id : null;
        }

        async function addItemToOrder(type, itemId, quantity = 1, price = null) {
            const orderId = pageOrderId();
            if (!orderId) {
                throw new Error('Не удалось определить заявку');
            }
            const endpoint = type === 'service' 
                ? `/api/orders/${orderId}/services`
                : `/api/orders/${orderId}/parts`;
            
            const body = type === 'service'
                ? { service_id: itemId, quantity, price }
                : { part_id: itemId, quantity, price };
            
            try {
                const response = await fetch(endpoint, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(body)
                });
                
                const data = await response.json();
                
                if (!response.ok || !data.success) {
                    throw new Error(data.error || `Не удалось добавить ${type === 'service' ? 'услугу' : 'товар'}`);
                }
                
                return { success: true, data };
            } catch (error) {
                console.error(`Ошибка при добавлении ${type === 'service' ? 'услуги' : 'товара'}:`, error);
                throw error;
            }
        }
        
        // Система комментариев и боковая панель
        document.addEventListener('DOMContentLoaded', function() {
            // Функции для работы с упоминаниями и файлами
            function parseMentions(text) {
                return escapeHtml(text).replace(/@(\w+)/g, '<span class="mention">@$1</span>');
            }
            
            function generateAttachmentsHtml(attachments) {
                if (!attachments) return '';
                const atts = attachments.split(',').filter(a => a);
                if (atts.length === 0) return '';
                return '<div class="mt-2">' + atts.map(att => {
                    const parts = att.split(':');
                    return `<a href="/api/comments/attachment/${parts[0]}" class="btn btn-sm btn-outline-secondary me-1 mb-1"><i class="fas fa-paperclip"></i> ${escapeHtml(parts[1])}</a>`;
                }).join('') + '</div>';
            }
            
            function escapeHtml(text) {
                const div = document.createElement('div');
                div.textContent = text;
                return div.innerHTML;
            }
            
            // Обработка загрузки файлов
            const fileInput = document.getElementById('commentFileInput');
            if (fileInput) {
                fileInput.addEventListener('change', function() {
                    const preview = document.getElementById('commentAttachmentsPreview');
                    if (!preview) return;
                    preview.innerHTML = '';
                    if (this.files.length > 0) {
                        Array.from(this.files).forEach(file => {
                            const div = document.createElement('div');
                            div.className = 'small text-muted mb-1';
                            div.innerHTML = `<i class="fas fa-file"></i> ${escapeHtml(file.name)} (${(file.size / 1024).toFixed(1)} KB)`;
                            preview.appendChild(div);
                        });
                    }
                });
            }
            
            const addCommentForm = document.getElementById('addCommentForm');
            const commentsList = document.getElementById('commentsList');
            const commentsSidebar = document.getElementById('commentsSidebar');
            const toggleCommentsBtn = document.getElementById('toggleCommentsBtn');
            const closeCommentsBtn = document.getElementById('closeCommentsBtn');
            
            // Переключение боковой панели комментариев
            if (toggleCommentsBtn && commentsSidebar) {
                toggleCommentsBtn.addEventListener('click', function() {
                    commentsSidebar.classList.toggle('active');
                });
            }
            
            if (closeCommentsBtn && commentsSidebar) {
                closeCommentsBtn.addEventListener('click', function() {
                    commentsSidebar.classList.remove('active');
                });
            }
            
            // Обновление счетчика комментариев
            function updateCommentsCount() {
                const count = commentsList.querySelectorAll('.comment-item').length;
                const countBadges = document.querySelectorAll('#commentsCount, #sidebarCommentsCount');
                countBadges.forEach(badge => {
                    if (badge) badge.textContent = count;
                });
            }
            
            // Обработка добавления комментария
            if (addCommentForm) {
                addCommentForm.addEventListener('submit', async function(e) {
                    e.preventDefault();
                    
                    const authorName = document.getElementById('commentAuthor').value.trim();
                    const commentText = document.getElementById('commentText').value.trim();
                    const isInternal = document.getElementById('isInternalComment')?.checked || false;
                    const fileInput = document.getElementById('commentFileInput');
                    const files = fileInput?.files || [];
                    
                    if (!commentText) {
                        showToast('Введите текст комментария', 'warning');
                        return;
                    }
                    const commentOrderId = pageOrderId();
                    if (!commentOrderId) {
                        showToast('Не удалось определить заявку', 'error');
                        return;
                    }
                    
                    // Загружаем файлы, если есть
                    const attachmentIds = [];
                    if (files.length > 0) {
                        for (const file of files) {
                            const formData = new FormData();
                            formData.append('file', file);
                            try {
                                const uploadResponse = await fetch('/api/comments/upload', {
                                    method: 'POST',
                                    body: formData
                                });
                                const uploadData = await uploadResponse.json();
                                if (uploadData.success) {
                                    attachmentIds.push(uploadData.attachment_id);
                                }
                            } catch (e) {
                                console.error('Ошибка загрузки файла:', e);
                            }
                        }
                    }
                    
                    try {
                        const response = await fetch(`/api/order/${commentOrderId}/comment`, {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                            },
                            body: JSON.stringify({
                                author_name: authorName,
                                comment_text: commentText,
                                is_internal: isInternal,
                                attachment_ids: attachmentIds
                            })
                        });
                        
                        const data = await response.json();
                        
                        if (data.success) {
                            // Очищаем форму
                            document.getElementById('commentText').value = '';
                            if (fileInput) fileInput.value = '';
                            if (document.getElementById('isInternalComment')) {
                                document.getElementById('isInternalComment').checked = false;
                            }
                            const preview = document.getElementById('commentAttachmentsPreview');
                            if (preview) preview.innerHTML = '';
                            
                            // Добавляем новый комментарий в начало списка
                            const comment = data.comment;
                            const mentionsHtml = comment.mentions ? parseMentions(comment.comment_text) : escapeHtml(comment.comment_text);
                            const attachmentsHtml = comment.attachments ? generateAttachmentsHtml(comment.attachments) : '';
                            const internalBadge = comment.is_internal ? '<span class="badge bg-warning text-dark small me-1"><i class="fas fa-eye-slash"></i> Внутренний</span>' : '';
                            const commentHtml = `
                                <div class="comment-item mb-2 p-2 border rounded${comment.is_internal ? ' internal-comment' : ''}" data-comment-id="${comment.id}">
                                    <div class="d-flex justify-content-between align-items-start">
                                        <div class="flex-grow-1">
                                            <div class="d-flex align-items-center mb-1">
                                                <strong class="me-2 small">${escapeHtml(comment.author_name)}</strong>
                                                ${internalBadge}
                                                <small class="text-muted">${formatDate(comment.created_at)}</small>
                                            </div>
                                            <p class="mb-0 small comment-text">${mentionsHtml}</p>
                                            ${attachmentsHtml}
                                        </div>
                                        <button class="btn btn-sm btn-danger delete-comment-btn ml-2" data-comment-id="${comment.id}" title="Удалить">
                                            <i class="fas fa-trash"></i>
                                        </button>
                                    </div>
                                </div>
                            `;
                            
                            showToast('Комментарий успешно добавлен', 'success');
                            
                            // Удаляем сообщение "Пока нет комментариев" если есть
                            const emptyMessage = commentsList.querySelector('.text-muted.text-center');
                            if (emptyMessage) {
                                emptyMessage.remove();
                            }
                            
                            // Добавляем новый комментарий
                            commentsList.insertAdjacentHTML('afterbegin', commentHtml);
                            
                            // Обновляем счетчик
                            updateCommentsCount();
                            
                            // Добавляем обработчик для кнопки удаления
                            const deleteBtn = commentsList.querySelector(`[data-comment-id="${comment.id}"] .delete-comment-btn`);
                            if (deleteBtn) {
                                deleteBtn.addEventListener('click', handleDeleteComment);
                            }
                            
                            // Прокручиваем к новому комментарию
                            commentsList.scrollTop = 0;
                        } else {
                            showToast(data.error || 'Не удалось добавить комментарий', 'error', 'Ошибка');
                        }
                    } catch (error) {
                        console.error('Error:', error);
                        showToast('Ошибка при добавлении комментария', 'error', 'Ошибка');
                    }
                });
            }
            
            // Обработка удаления комментария
            function handleDeleteComment(e) {
                const commentId = e.target.closest('.delete-comment-btn').getAttribute('data-comment-id');
                
                if (!confirm('Вы уверены, что хотите удалить этот комментарий?')) {
                    return;
                }
                
                fetch(`/api/order/comment/${commentId}`, {
                    method: 'DELETE'
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        // Удаляем элемент комментария из DOM
                        const commentItem = document.querySelector(`[data-comment-id="${commentId}"]`);
                        if (commentItem) {
                            commentItem.remove();
                            
                            // Обновляем счетчик
                            updateCommentsCount();
                            
                            // Если комментариев не осталось, показываем сообщение
                            if (commentsList.querySelectorAll('.comment-item').length === 0) {
                                const emptyMsg = commentsList.querySelector('.text-muted.text-center');
                                if (!emptyMsg) {
                                    DOMUtils.clear(commentsList);
                                    const emptyP = DOMUtils.createElement('p', 'Пока нет комментариев', {
                                        'class': 'text-muted text-center small'
                                    });
                                    commentsList.appendChild(emptyP);
                                }
                            }
                            
                            showToast('Комментарий успешно удален', 'success');
                        }
                    } else {
                        showToast(data.error || 'Не удалось удалить комментарий', 'error', 'Ошибка');
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    showToast('Ошибка при удалении комментария', 'error', 'Ошибка');
                });
            }
            
            // Добавляем обработчики для всех кнопок удаления
            document.querySelectorAll('.delete-comment-btn').forEach(btn => {
                btn.addEventListener('click', handleDeleteComment);
            });
            
            // Обработка скрытия/показа заявки
            const hideOrderBtn = document.getElementById('hideOrderBtn');
            
            if (hideOrderBtn) {
                hideOrderBtn.addEventListener('click', async function() {
                    const orderId = parseInt(hideOrderBtn.getAttribute('data-order-id'), 10) || pageOrderId();
                    if (!orderId) {
                        showToast('Не удалось определить заявку', 'error');
                        return;
                    }
                    const currentHidden = parseInt(hideOrderBtn.getAttribute('data-hidden') ?? '0', 10) || 0;
                    const newHidden = currentHidden === 1 ? 0 : 1;
                    
                    // Запрашиваем подтверждение
                    const action = newHidden === 0 ? 'скрыть' : 'показать';
                    if (!confirm(`Вы уверены, что хотите ${action} эту заявку?`)) {
                        return;
                    }
                    
                    try {
                        const response = await fetch(`/api/order/${orderId}/toggle-visibility`, {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                            },
                            body: JSON.stringify({
                                hidden: newHidden,
                                changed_by: 'Администратор',
                                reason: `Заявка ${action}на пользователем`
                            })
                        });
                        
                        const data = await response.json();
                        
                        if (data.success) {
                            // Обновляем UI
                            hideOrderBtn.setAttribute('data-hidden', newHidden);
                            const nextActionTitle = newHidden === 0 ? 'Показать заявку' : 'Скрыть заявку';
                            hideOrderBtn.setAttribute('title', nextActionTitle);
                            hideOrderBtn.setAttribute('aria-label', nextActionTitle);
                            
                            // Показываем сообщение
                            const actionDone = newHidden === 0 ? 'Заявка скрыта' : 'Заявка снова отображается';
                            showToast(data.message || actionDone, 'success');
                            
                            // Если заявка скрыта, перенаправляем на список заявок
                            if (newHidden === 0) {
                                setTimeout(() => {
                                    window.location.href = '/all_orders?view=registry&status=in_progress';
                                }, 1000);
                            }
                        } else {
                            showToast(data.error || 'Не удалось изменить видимость заявки', 'error', 'Ошибка');
                        }
                    } catch (error) {
                        console.error('Ошибка при изменении видимости заявки:', error);
                        showToast('Произошла ошибка при изменении видимости заявки', 'error', 'Ошибка');
                    }
                });
            }

            // Полноценное мягкое удаление заявки
            const deleteOrderBtn = document.getElementById('deleteOrderBtn');
            const confirmDeleteOrderBtn = document.getElementById('confirmDeleteOrderBtn');
            const deleteOrderReasonInput = document.getElementById('deleteOrderReasonInput');
            const deleteOrderModalEl = document.getElementById('deleteOrderModal');

            if (deleteOrderBtn && deleteOrderModalEl) {
                const deleteModal = new bootstrap.Modal(deleteOrderModalEl);
                deleteOrderBtn.addEventListener('click', function() {
                    if (deleteOrderReasonInput) deleteOrderReasonInput.value = '';
                    deleteModal.show();
                });
            }

            if (confirmDeleteOrderBtn && deleteOrderBtn) {
                confirmDeleteOrderBtn.addEventListener('click', async function() {
                    const orderId = parseInt(deleteOrderBtn.getAttribute('data-order-id'), 10) || pageOrderId();
                    const orderUuid = deleteOrderBtn.getAttribute('data-order-uuid');
                    const reason = (deleteOrderReasonInput?.value || '').trim();

                    if (!orderId) {
                        showToast('Не удалось определить заявку', 'error');
                        return;
                    }

                    if (!reason) {
                        showToast('Укажите причину удаления', 'warning');
                        deleteOrderReasonInput?.focus();
                        return;
                    }

                    confirmDeleteOrderBtn.disabled = true;
                    try {
                        const response = await fetch(`/api/order/${orderId}/delete`, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ reason: reason })
                        });
                        const data = await response.json();
                        if (!data.success) {
                            showToast(data.error || 'Не удалось удалить заявку', 'error', 'Ошибка');
                            return;
                        }

                        showToast(`Заявка #${orderUuid || orderId} удалена`, 'success');
                        setTimeout(() => {
                            window.location.href = (window.NIKA_ORDER_PAGE && window.NIKA_ORDER_PAGE.allOrdersUrl) || '/all_orders?view=registry&status=in_progress';
                        }, 900);
                    } catch (error) {
                        console.error('Ошибка при удалении заявки:', error);
                        showToast('Произошла ошибка при удалении заявки', 'error', 'Ошибка');
                    } finally {
                        confirmDeleteOrderBtn.disabled = false;
                    }
                });
            }
        });
