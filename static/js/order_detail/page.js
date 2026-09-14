/* Extracted from templates/order_detail.html — keep in sync with NIKA_ORDER_PAGE bootstrap. */
function numericOrderId() {
    const raw = (window.NIKA_ORDER_PAGE && window.NIKA_ORDER_PAGE.orderId) || window.ORDER_ID;
    const id = parseInt(raw, 10);
    return Number.isFinite(id) && id > 0 ? id : null;
}

// Инициализация динамического dropdown статуса
        // Пробуем несколько способов инициализации для надежности
        function initStatusDropdown() {
            var statusDropdownElement = document.getElementById('statusDropdownBtn');
            if (!statusDropdownElement) {
                Logger.warn('Элемент #statusDropdownBtn не найден');
                return;
            }

            // Способ 1: Явная инициализация через Bootstrap API
            if (typeof bootstrap !== 'undefined' && bootstrap.Dropdown) {
                try {
                    // Удаляем старый экземпляр, если есть
                    var existingDropdown = bootstrap.Dropdown.getInstance(statusDropdownElement);
                    if (existingDropdown) {
                        existingDropdown.dispose();
                    }
                    // Создаем новый экземпляр
                    var dropdown = new bootstrap.Dropdown(statusDropdownElement);
                    Logger.log('Dropdown инициализирован через Bootstrap API');
                    return;
                } catch (error) {
                    console.error('Ошибка инициализации dropdown через API:', error);
                }
            }

            // Способ 2: Bootstrap 5 должен работать автоматически с data-bs-toggle="dropdown"
            // Но если не работает, пробуем принудительно инициализировать
            Logger.log('Пробуем автоматическую инициализацию через data-bs-toggle');
        }

        // Инициализация при загрузке страницы
        document.addEventListener('DOMContentLoaded', function() {
            Logger.log('DOM загружен, инициализируем dropdown статуса');
            
            // Инициализируем Bootstrap dropdown для статуса
            var statusDropdownElement = document.getElementById('statusDropdownBtn');
            if (statusDropdownElement) {
                Logger.log('Найден элемент statusDropdownBtn');
                
                if (typeof bootstrap !== 'undefined' && bootstrap.Dropdown) {
                    try {
                        // Удаляем старый экземпляр, если есть
                        var existingDropdown = bootstrap.Dropdown.getInstance(statusDropdownElement);
                        if (existingDropdown) {
                            existingDropdown.dispose();
                        }
                        // Создаем новый экземпляр
                        new bootstrap.Dropdown(statusDropdownElement);
                        Logger.log('Bootstrap dropdown инициализирован');
                    } catch (error) {
                        console.error('Ошибка инициализации dropdown:', error);
                    }
                } else {
                    Logger.warn('Bootstrap не найден');
                }
            } else {
                Logger.warn('Элемент statusDropdownBtn не найден');
            }
        });

        // Обработчик клика на элемент dropdown меню статуса (глобальный, не внутри DOMContentLoaded)
        document.addEventListener('click', function(e) {
            const dropdownItem = e.target.closest('.status-dropdown-item');
            if (!dropdownItem) return;
            
            e.preventDefault();
            e.stopPropagation();
            
            Logger.log('Клик по элементу статуса:', dropdownItem);
            
            const dropdown = dropdownItem.closest('.dropdown');
            if (!dropdown) {
                console.error('Не найден родительский dropdown');
                return;
            }
            
            const button = dropdown.querySelector('.quick-status-btn');
            if (!button) {
                console.error('Не найдена кнопка статуса');
                return;
            }
            
            const orderId = button.getAttribute('data-order-id');
            const orderDbId = button.getAttribute('data-order-db-id');
            const statusId = dropdownItem.getAttribute('data-status-id');
            const statusName = dropdownItem.getAttribute('data-status-name');
            const statusColor = dropdownItem.getAttribute('data-status-color');
            const statusCode = dropdownItem.getAttribute('data-status-code') || '';
            const currentStatusId = button.getAttribute('data-status-id') || '';

            // Если выбран текущий статус, ничего не делаем (не запускаем повторные сценарии/модалки).
            if (String(currentStatusId) === String(statusId || '')) {
                if (typeof bootstrap !== 'undefined' && bootstrap.Dropdown) {
                    const bsDropdown = bootstrap.Dropdown.getInstance(button);
                    if (bsDropdown) bsDropdown.hide();
                }
                return;
            }
            
            console.log('Данные для обновления:', {
                orderId,
                orderDbId,
                statusId,
                statusName,
                statusColor,
                statusCode
            });
            
            // Не обновляем кнопку до успешного ответа API — иначе при ошибке покажется неверный статус
            // Обновляем активный элемент в меню (подсветка выбранного пункта)
            dropdown.querySelectorAll('.status-dropdown-item').forEach(item => {
                item.classList.remove('active');
            });
            dropdownItem.classList.add('active');
            
            // Закрываем dropdown
            if (typeof bootstrap !== 'undefined' && bootstrap.Dropdown) {
                const bsDropdown = bootstrap.Dropdown.getInstance(button);
                if (bsDropdown) {
                    bsDropdown.hide();
                }
            }
            
            // Вызываем функцию обновления статуса
            if (window.updateOrderStatus) {
                console.log('Вызываем updateOrderStatus');
                updateOrderStatus(button, orderId, orderDbId, statusId, statusName, statusColor, statusCode);
            } else {
                console.error('Функция updateOrderStatus не найдена');
            }
        });

        const CLOSED_PRINT_MODE = (window.NIKA_ORDER_PAGE && window.NIKA_ORDER_PAGE.closePrintMode) || 'choice';

        document.getElementById('loadMoreOrderHistory')?.addEventListener('click', function() {
            const btn = this;
            const next = Number(btn.dataset.page || '2');
            const id = (typeof ORDER_ID !== 'undefined') ? ORDER_ID : null;
            if (!id) return;
            btn.disabled = true;
            fetch('/api/order/' + id + '/action-logs?page=' + next, { credentials: 'same-origin' })
                .then(r => r.json())
                .then(data => {
                    const tbody = document.querySelector('#history-pane tbody');
                    if (data && data.success && tbody) {
                        (data.items || []).forEach(item => {
                            const tr = document.createElement('tr');
                            const when = (item.created_at || '').split(' ');
                            tr.innerHTML = '<td><small>' + (when[0] || '') + '</small></td>'
                                + '<td><small class="text-muted">' + ((when[1] || '').slice(0, 5)) + '</small></td>'
                                + '<td>' + (item.title || '').replace(/</g, '&lt;') + '</td>'
                                + '<td><small>' + (item.username || '') + '</small></td>';
                            tbody.appendChild(tr);
                        });
                    }
                    if (data && data.has_more) {
                        btn.dataset.page = String(next + 1);
                        btn.disabled = false;
                    } else {
                        btn.remove();
                    }
                })
                .catch(() => { btn.disabled = false; });
        });

        window._orderPrintBundle = window._orderPrintBundle || null;
        window.ensureOrderPrintBundle = function() {
            if (window._orderPrintBundle) return Promise.resolve(window._orderPrintBundle);
            const id = (typeof ORDER_ID !== 'undefined') ? ORDER_ID : null;
            if (!id) return Promise.resolve(null);
            return fetch('/api/order/' + id + '/print-html', { credentials: 'same-origin' })
                .then(r => r.json())
                .then(data => {
                    if (!data || !data.success) return null;
                    window._orderPrintBundle = data;
                    if (data.customer) {
                        const pv = document.querySelector('.print-view');
                        if (pv) pv.innerHTML = data.customer;
                    }
                    if (data.sales_receipt) {
                        const el = document.getElementById('salesReceiptTemplateRendered');
                        if (el) el.innerHTML = data.sales_receipt;
                    }
                    if (data.work_act) {
                        const el = document.getElementById('workActTemplateRendered');
                        if (el) el.innerHTML = data.work_act;
                    }
                    return data;
                })
                .catch(() => null);
        };

        window.printRenderedTemplate = function(templateType) {
            const run = function() {
                if (templateType === 'both') {
                    window.printRenderedTemplate('sales_receipt');
                    setTimeout(() => window.printRenderedTemplate('work_act'), 700);
                    return;
                }
                if (!templateType || templateType === 'customer') {
                    window.print();
                    return;
                }
                const map = {
                    sales_receipt: 'salesReceiptTemplateRendered',
                    work_act: 'workActTemplateRendered',
                };
                const el = document.getElementById(map[templateType] || '');
                const html = el ? (el.innerHTML || '').trim() : '';
                if (!html) {
                    showToast('Шаблон не настроен в /settings', 'warning');
                    return;
                }
                const w = window.open('', '_blank', 'width=1000,height=800');
                if (!w) {
                    showToast('Разрешите всплывающие окна для печати', 'warning');
                    return;
                }
                const printPageSize = (window.NIKA_ORDER_PAGE && window.NIKA_ORDER_PAGE.printPageSize) || 'A4';
                const printMarginMm = Number(window.NIKA_ORDER_PAGE && window.NIKA_ORDER_PAGE.printMarginMm) || 3;
                w.document.write(`<!doctype html><html><head><meta charset="utf-8"><title>Печать</title><style>@page{size:${printPageSize};margin:${printMarginMm}mm;}html,body{font-family:Arial,sans-serif;margin:0;padding:0;}body{padding:0;}table{border-collapse:collapse;width:100%;}td,th{border:1px solid #ddd;padding:6px;}</style></head><body>${html}</body></html>`);
                w.document.close();
                w.focus();
                w.print();
            };
            const printReady = !!(window.NIKA_ORDER_PAGE && window.NIKA_ORDER_PAGE.printTemplatesReady);
            if (!printReady && !window._orderPrintBundle) {
                window.ensureOrderPrintBundle().then(function() { run(); });
                return;
            }
            run();
        };

        function handleClosedPrintFlow() {
            const mode = String(CLOSED_PRINT_MODE || 'choice');
            if (mode === 'none') return;
            if (mode === 'sales_receipt') return window.printRenderedTemplate('sales_receipt');
            if (mode === 'work_act') return window.printRenderedTemplate('work_act');
            if (mode === 'both') return window.printRenderedTemplate('both');
            const modalEl = document.getElementById('closedPrintChoiceModal');
            if (modalEl && window.bootstrap && window.bootstrap.Modal) {
                new bootstrap.Modal(modalEl).show();
            }
        }

        function scheduleReloadAfterPrintFlow(defaultDelayMs = 1000) {
            const mode = String(CLOSED_PRINT_MODE || 'choice');
            const reloadOnce = () => {
                // Без open_payment_modal в URL — иначе после reload модалка оплаты откроется снова
                const url = new URL(window.location.href);
                url.searchParams.delete('open_payment_modal');
                const qs = url.searchParams.toString();
                window.location.href = url.pathname + (qs ? '?' + qs : '') + url.hash;
            };
            if (mode !== 'choice') {
                setTimeout(reloadOnce, defaultDelayMs);
                return;
            }

            const modalEl = document.getElementById('closedPrintChoiceModal');
            if (!modalEl) {
                setTimeout(reloadOnce, defaultDelayMs);
                return;
            }

            let reloaded = false;
            const reloadSafe = () => {
                if (reloaded) return;
                reloaded = true;
                reloadOnce();
            };
            modalEl.addEventListener('hidden.bs.modal', reloadSafe, { once: true });
            // Fallback: если модалка не появилась/не закрылась, всё равно обновим страницу.
            setTimeout(reloadSafe, 15000);
        }

        function stripOpenPaymentModalFromUrl() {
            const url = new URL(window.location.href);
            if (!url.searchParams.has('open_payment_modal')) return;
            url.searchParams.delete('open_payment_modal');
            const qs = url.searchParams.toString();
            history.replaceState(null, '', url.pathname + (qs ? '?' + qs : '') + url.hash);
        }

        function reloadOrderDetailClean() {
            const url = new URL(window.location.href);
            url.searchParams.delete('open_payment_modal');
            const qs = url.searchParams.toString();
            window.location.href = url.pathname + (qs ? '?' + qs : '') + url.hash;
        }

        function runAutoPrintFromQueryIfNeeded() {
            const url = new URL(window.location.href);
            const flag = (url.searchParams.get('print') || url.searchParams.get('auto_print') || '').toLowerCase();
            const shouldPrint = flag === '1' || flag === 'true' || flag === 'yes' || flag === 'customer' || flag === 'receipt';
            if (!shouldPrint) return;
            url.searchParams.delete('print');
            url.searchParams.delete('auto_print');
            const qs = url.searchParams.toString();
            history.replaceState(null, '', url.pathname + (qs ? '?' + qs : '') + url.hash);
            setTimeout(() => { window.print(); }, 250);
        }

        let pendingClosedPrintAfterPayment = false;

        // Функция для обновления статуса заявки (как в all_orders.html)
        window.updateOrderStatus = async function(buttonElement, orderId, orderDbId, statusId, statusName, statusColor, statusCode) {
            console.log('updateOrderStatus вызвана:', {
                buttonElement: buttonElement.tagName,
                orderId,
                orderDbId,
                statusId,
                statusName,
                statusColor,
                statusCode
            });
            
            // Если функция вызвана со старым API (select), преобразуем в новый формат
            if (buttonElement.tagName === 'SELECT') {
                statusId = buttonElement.value;
                const selectedOption = buttonElement.options[buttonElement.selectedIndex];
                statusName = selectedOption.text;
                statusColor = selectedOption.dataset.color || buttonElement.dataset.statusColor || '#6c757d';
                statusCode = selectedOption.dataset.code || 'unknown';
                
                // Находим соответствующий button в том же row
                const row = buttonElement.closest('tr');
                buttonElement = row.querySelector('.quick-status-btn');
                if (!buttonElement) {
                    console.error('ERROR: Не найден button элемент');
                    return;
                }
            }
            
            // Текущий статус (до смены) — для отката при ошибке
            const originalStatusId = buttonElement.dataset.statusId || '';
            const originalStatusName = buttonElement.textContent.trim();
            const originalStatusColor = buttonElement.dataset.statusColor || buttonElement.style.backgroundColor || '#6c757d';
            buttonElement.dataset.originalStatusId = originalStatusId;
            buttonElement.dataset.originalStatusName = originalStatusName;
            buttonElement.dataset.originalStatusColor = originalStatusColor;

            // Защита от повторного применения того же статуса.
            if (String(originalStatusId) === String(statusId || '')) {
                return;
            }
            
            // Проверяем флаги статуса перед отправкой (если доступны)
            // Это предварительная проверка, полная проверка будет на сервере
            // Ищем элемент dropdown с data-атрибутами
            const statusDropdownItem = document.querySelector(`.status-dropdown-item[data-status-id="${statusId}"]`);
            let requiresComment = false;
            
            if (statusDropdownItem) {
                requiresComment = statusDropdownItem.dataset.requiresComment === '1' || statusDropdownItem.dataset.requiresComment === 'true';
                // Флаг requires_warranty удален - гарантия берется из карточки товара/услуги
            }

            const blocksEditTarget = statusDropdownItem && (statusDropdownItem.dataset.blocksEdit === '1' || statusDropdownItem.dataset.blocksEdit === 'true');
            const isFinalTarget = statusDropdownItem && (statusDropdownItem.dataset.isFinal === '1' || statusDropdownItem.dataset.isFinal === 'true');
            if ((blocksEditTarget || isFinalTarget) && window.NikaDiagnostics && window.NikaDiagnostics.guardStatusChange) {
                const numericId = (typeof ORDER_ID !== 'undefined') ? ORDER_ID : orderDbId;
                const shouldProceed = await window.NikaDiagnostics.guardStatusChange({
                    numericId: numericId,
                    orderId: orderId,
                    orderDbId: numericId,
                    statusId: statusId,
                    statusName: statusName,
                    statusColor: statusColor,
                    statusCode: statusCode,
                    buttonElement: buttonElement,
                });
                if (!shouldProceed) {
                    return;
                }
            }
            
            // Валидация перед сменой статуса
            let comment = '';
            if (requiresComment) {
                comment = prompt('Для смены статуса требуется комментарий. Введите комментарий:');
                if (!comment || !comment.trim()) {
                    showToast('Комментарий обязателен для смены этого статуса', 'warning');
                    buttonElement.disabled = false;
                    buttonElement.style.opacity = '1';
                    buttonElement.textContent = originalStatusName;
                    buttonElement.style.backgroundColor = originalStatusColor;
                    buttonElement.style.borderColor = originalStatusColor;
                    return;
                }
            }
            
            // Визуальная индикация загрузки
            buttonElement.disabled = true;
            buttonElement.style.opacity = '0.6';
            DOMUtils.clear(buttonElement);
            const spinner = DOMUtils.createElement('span', '', {'class': 'spinner-border spinner-border-sm me-1'});
            const text = document.createTextNode('Обновление...');
            buttonElement.appendChild(spinner);
            buttonElement.appendChild(text);
            
            try {
                // Обрабатываем statusId - может быть пустой строкой, null, undefined или числом
                let statusIdValue = null;
                if (statusId && statusId !== '' && statusId !== 'null' && statusId !== 'undefined') {
                    const parsed = parseInt(statusId);
                    if (!isNaN(parsed) && parsed > 0) {
                        statusIdValue = parsed;
                    }
                }
                
                const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
                const response = await fetch(`/api/order/${orderId}/status`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken
                    },
                    body: JSON.stringify({
                        status_id: statusIdValue,
                        comment: requiresComment ? (comment || '') : (comment || undefined),
                        client_instance_id: window.nikaStaffClientInstanceId || ''
                    })
                });
                
                // Получаем текст ответа для отладки
                const responseText = await response.text();
                
                let data;
                try {
                    data = JSON.parse(responseText);
                } catch (e) {
                    console.error('ERROR: Не удалось распарсить JSON:', e, responseText);
                    throw new Error(`Ошибка парсинга ответа сервера: ${responseText.substring(0, 200)}`);
                }
                
                // Проверяем статус ответа
                if (!response.ok) {
                    const errorMsg = data.error || data.message || `HTTP ${response.status}: ${response.statusText}`;
                    throw new Error(errorMsg);
                }
                
                // Проверяем успешность операции
                if (data && data.success) {
                    // Показываем уведомление об успешном изменении статуса
                    const finalStatusName = data.status_name || statusName || 'Не указан';
                    showToast(`Статус изменен на: ${finalStatusName}`, 'success', null, 3000);
                    
                    // Обработка триггеров
                    if (data.triggers_payment_modal) {
                        // Проверяем, есть ли товары/услуги в заявке
                        const orderTotal = Number(window.NIKA_ORDER_PAGE && window.NIKA_ORDER_PAGE.orderTotal) || 0;
                        let shouldOpenModal = true;
                        
                        if (orderTotal <= 0) {
                            showToast('Нельзя открыть окно оплаты: в заявке нет товаров или услуг', 'warning', null, 3000);
                            shouldOpenModal = false;
                        } else {
                            // Проверяем долг - если долг отсутствует, не открываем модалку
                            let orderDebt = Number(window.NIKA_ORDER_PAGE && window.NIKA_ORDER_PAGE.orderDebt) || 0;
                            const orderDebtEl = document.querySelector('[data-order-debt]');
                            if (orderDebtEl) {
                                const debtValue = orderDebtEl.getAttribute('data-order-debt-value');
                                if (debtValue !== null && debtValue !== '') {
                                    orderDebt = parseFloat(debtValue) || orderDebt;
                                } else {
                                    const debtText = orderDebtEl.textContent.replace(/[^\d.,]/g, '').replace(',', '.');
                                    orderDebt = parseFloat(debtText) || orderDebt;
                                }
                            }
                            
                            if (orderDebt <= 0) {
                                showToast('Нельзя открыть окно оплаты: долг отсутствует', 'info', null, 3000);
                                shouldOpenModal = false;
                            }
                        }
                        
                        // Открываем окно оплаты только если все проверки пройдены
                        if (shouldOpenModal) {
                            setTimeout(() => {
                                openPaymentModalWithDebt();
                            }, 500);
                        }
                    }
                    
                    if (data.accrues_salary) {
                        // Реальное создание/пересчёт начислений (не повторное закрытие)
                        showToast('Зарплата начислена', 'info', null, 2000);
                        if (typeof loadSalaryInfo === 'function') {
                            loadSalaryInfo();
                        }
                    } else if (data.salary_transferred) {
                        showToast('Начисления перенесены на текущего исполнителя', 'info', null, 2500);
                        if (typeof loadSalaryInfo === 'function') {
                            loadSalaryInfo();
                        }
                    }
                    
                    // Блокировка редактирования заявки (для blocks_edit или is_final)
                    if (data.blocks_edit || data.is_final) {
                        const blockedMsg = 'Сначала откройте заявку';
                        const editButton = document.getElementById('editOrderBtn') || document.querySelector('[data-bs-target="#editOrderModal"]');
                        if (editButton) {
                            editButton.style.opacity = '0.5';
                            editButton.style.cursor = 'not-allowed';
                            editButton.title = blockedMsg;
                            editButton.setAttribute('aria-disabled', 'true');
                            editButton.removeAttribute('data-bs-toggle');
                            editButton.removeAttribute('data-bs-target');
                            editButton.addEventListener('click', function blockEdit(e) {
                                e.preventDefault();
                                e.stopImmediatePropagation();
                                showToast('Сначала откройте заявку', 'warning', 'Заявка закрыта');
                                return false;
                            }, true);
                        }
                        const addItemsBtn = document.getElementById('openAddItemsModalBtn');
                        if (addItemsBtn) {
                            addItemsBtn.style.opacity = '0.5';
                            addItemsBtn.style.cursor = 'not-allowed';
                            addItemsBtn.title = blockedMsg;
                            addItemsBtn.setAttribute('aria-disabled', 'true');
                            addItemsBtn.removeAttribute('data-bs-toggle');
                            addItemsBtn.removeAttribute('data-bs-target');
                            addItemsBtn.addEventListener('click', function blockAddItems(e) {
                                e.preventDefault();
                                e.stopImmediatePropagation();
                                showToast(blockedMsg, 'warning', 'Заявка закрыта');
                                return false;
                            }, true);
                        }
                        const addPaymentBtn = document.getElementById('addPaymentBtn');
                        if (addPaymentBtn) {
                            addPaymentBtn.style.opacity = '0.5';
                            addPaymentBtn.style.cursor = 'not-allowed';
                            addPaymentBtn.title = blockedMsg;
                            addPaymentBtn.setAttribute('aria-disabled', 'true');
                            addPaymentBtn.removeAttribute('data-bs-toggle');
                            addPaymentBtn.removeAttribute('data-bs-target');
                            addPaymentBtn.addEventListener('click', function blockAddPayment(e) {
                                e.preventDefault();
                                e.stopImmediatePropagation();
                                showToast(blockedMsg, 'warning', 'Заявка закрыта');
                                return false;
                            }, true);
                        }
                    }
                    
                    // Обновляем список комментариев, если был добавлен комментарий
                    if (data.comment_added) {
                        // Просто перезагружаем страницу комментариев (если открыта)
                        // Или показываем уведомление, что комментарий добавлен
                        showToast('Комментарий добавлен в раздел "Комментарии"', 'info', null, 2000);
                        // Можно также обновить счетчик комментариев, если он есть на странице
                        const commentsCountBadge = document.getElementById('commentsCount');
                        if (commentsCountBadge) {
                            // Увеличиваем счетчик на 1
                            const currentCount = parseInt(commentsCountBadge.textContent) || 0;
                            commentsCountBadge.textContent = currentCount + 1;
                        }
                    }
                    
                    // Обновляем визуальное отображение кнопки
                    const finalStatusColor = data.status_color || statusColor || '#6c757d';
                    
                    buttonElement.textContent = finalStatusName;
                    buttonElement.style.backgroundColor = finalStatusColor;
                    buttonElement.style.borderColor = finalStatusColor;
                    buttonElement.dataset.statusId = statusId || '';
                    buttonElement.dataset.statusColor = finalStatusColor;
                    
                    // Функция для преобразования hex в RGB
                    function hexToRgb(hex) {
                        const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
                        return result ? {
                            r: parseInt(result[1], 16),
                            g: parseInt(result[2], 16),
                            b: parseInt(result[3], 16)
                        } : { r: 108, g: 117, b: 125 }; // По умолчанию серый цвет
                    }
                    
                    // Показываем уведомление по центру сверху с цветом статуса
                    const toast = document.createElement('div');
                    toast.className = 'alert alert-dismissible fade show position-fixed';
                    // Используем цвет статуса для фона
                    const statusBgColor = finalStatusColor || '#6c757d';
                    // Определяем цвет текста (светлый или темный) в зависимости от яркости фона
                    const rgb = hexToRgb(statusBgColor);
                    const brightness = (rgb.r * 299 + rgb.g * 587 + rgb.b * 114) / 1000;
                    const textColor = brightness > 128 ? '#000' : '#fff';
                    
                    toast.style.cssText = `
                        top: 20px;
                        left: 50%;
                        transform: translateX(-50%);
                        z-index: 9999;
                        min-width: 300px;
                        max-width: 600px;
                        background-color: ${statusBgColor};
                        color: ${textColor};
                        border: 2px solid ${statusBgColor};
                        border-radius: 8px;
                        box-shadow: 0 4px 20px rgba(0,0,0,0.3);
                        padding: 15px 25px;
                        font-size: 14px;
                        text-align: center;
                    `;
                    
                    // Используем числовой ID заявки вместо UUID
                    const displayOrderId = orderDbId || orderId;
                    
                    // Безопасное создание toast уведомления
                    const toastContent = DOMUtils.createElement('div', '', {
                        'style': 'display: flex; align-items: center; justify-content: center; gap: 10px;'
                    });
                    
                    const icon = DOMUtils.createElement('i', '', {
                        'class': 'fas fa-check-circle',
                        'style': 'font-size: 20px;'
                    });
                    
                    const textDiv = DOMUtils.createElement('div', '');
                    const strong = DOMUtils.createElement('strong', 'Статус обновлен!', {
                        'style': 'display: block; margin-bottom: 3px;'
                    });
                    const span = DOMUtils.createElement('span', `Заявка #${displayOrderId} теперь в статусе "${finalStatusName}"`);
                    
                    textDiv.appendChild(strong);
                    textDiv.appendChild(span);
                    
                    const closeBtn = DOMUtils.createElement('button', '', {
                        'type': 'button',
                        'class': 'btn-close',
                        'data-bs-dismiss': 'alert',
                        'style': `filter: ${brightness > 128 ? 'invert(1)' : 'invert(0)'};`
                    });
                    
                    toastContent.appendChild(icon);
                    toastContent.appendChild(textDiv);
                    toast.appendChild(toastContent);
                    toast.appendChild(closeBtn);
                    
                    document.body.appendChild(toast);
                    
                    // Автоматически скрываем уведомление через 3 секунды с анимацией
                    setTimeout(() => {
                        toast.style.opacity = '0';
                        toast.style.transition = 'opacity 0.3s ease-out';
                        setTimeout(() => {
                            toast.remove();
                        }, 300);
                    }, 3000);
                    
                    // Обновляем оригинальное значение
                    buttonElement.dataset.originalStatusId = statusId || '';
                    buttonElement.dataset.originalStatusName = finalStatusName;
                    buttonElement.dataset.originalStatusColor = finalStatusColor;

                    // Важно: НЕ перезагружаем страницу, если нужно открыть модалку оплаты/начисления.
                    // Иначе modal откроется и тут же закроется из-за reload (симптом: "пропадает через секунду").
                    const shouldOpenPayment = !!data.triggers_payment_modal;
                    const shouldReload = !shouldOpenPayment;

                    const closedByCode = String(statusCode || '').toLowerCase() === 'closed';
                    const closedByName = String(finalStatusName || '').toLowerCase().includes('закры');
                    // Если нужно сразу открыть модалку оплаты долга, не перекрываем её окнами печати.
                    if (closedByCode || closedByName) {
                        if (shouldOpenPayment) {
                            pendingClosedPrintAfterPayment = true;
                        } else {
                            handleClosedPrintFlow();
                        }
                    }

                    if (shouldReload) {
                    if (closedByCode || closedByName) {
                        scheduleReloadAfterPrintFlow(1000);
                    } else {
                        setTimeout(() => {
                            window.location.reload();
                        }, 1000);
                    }
                    }
                } else {
                    // Откатываем изменение при ошибке
                    buttonElement.textContent = buttonElement.dataset.originalStatusName || originalStatusName;
                    buttonElement.style.backgroundColor = buttonElement.dataset.originalStatusColor || originalStatusColor;
                    buttonElement.style.borderColor = buttonElement.dataset.originalStatusColor || originalStatusColor;
                    buttonElement.dataset.statusId = buttonElement.dataset.originalStatusId || originalStatusId;
                    
                    // Показываем детальное сообщение об ошибке
                    const errorMsg = data.error || data.message || 'Не удалось обновить статус';
                    Logger.error('Ошибка обновления статуса:', {
                        orderId: orderId,
                        statusId: statusId,
                        statusIdValue: statusIdValue,
                        response: data,
                        error: errorMsg
                    });
                    showToast(errorMsg, 'error', 'Ошибка обновления статуса');
                }
            } catch (error) {
                Logger.error('Ошибка при обновлении статуса:', error);
                
                // Откатываем кнопку к фактическому статусу (до попытки смены)
                const prevName = buttonElement.dataset.originalStatusName || originalStatusName;
                const prevColor = buttonElement.dataset.originalStatusColor || originalStatusColor;
                const prevId = buttonElement.dataset.originalStatusId || originalStatusId;
                buttonElement.textContent = prevName;
                buttonElement.style.backgroundColor = prevColor;
                buttonElement.style.borderColor = prevColor;
                buttonElement.dataset.statusId = prevId;
                if (prevColor) buttonElement.dataset.statusColor = prevColor;
                
                // Восстанавливаем подсветку пункта в dropdown
                const dropdown = buttonElement.closest('.dropdown');
                if (dropdown) {
                    dropdown.querySelectorAll('.status-dropdown-item').forEach(item => {
                        item.classList.toggle('active', String(item.getAttribute('data-status-id')) === String(prevId));
                    });
                }

                if (window.NikaDiagnostics && window.NikaDiagnostics.isMissingDiagnosticsError(error.message)) {
                    const numericId = (typeof ORDER_ID !== 'undefined') ? ORDER_ID : orderDbId;
                    window.NikaDiagnostics.openForOrder(numericId, {
                        pendingStatus: {
                            buttonElement: buttonElement,
                            orderId: orderId,
                            orderDbId: numericId,
                            statusId: statusId,
                            statusName: statusName,
                            statusColor: statusColor,
                            statusCode: statusCode,
                        },
                    });
                    return;
                }
                
                // Показываем ошибку
                const toast = document.createElement('div');
                toast.className = 'alert alert-danger alert-dismissible fade show position-fixed';
                toast.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
                const strong = DOMUtils.createElement('strong', 'Ошибка!');
                const errorText = document.createTextNode(` Не удалось обновить статус: ${error.message}`);
                const closeBtn = DOMUtils.createElement('button', '', {
                    'type': 'button',
                    'class': 'btn-close',
                    'data-bs-dismiss': 'alert'
                });
                toast.appendChild(strong);
                toast.appendChild(errorText);
                toast.appendChild(closeBtn);
                document.body.appendChild(toast);
                
                setTimeout(() => {
                    toast.remove();
                }, 5000);
            } finally {
                // Восстанавливаем элемент
                buttonElement.disabled = false;
                buttonElement.style.opacity = '1';
            }
        };

        runAutoPrintFromQueryIfNeeded();

        // Форматирование телефона в форме редактирования
        const editPhoneInput = document.getElementById('editPhone');
        
        if (editPhoneInput) {
            function normalizePhoneClient(value) {
                if (window.nikaNormalizePhone) return window.nikaNormalizePhone(value);
                const digits = value.replace(/\D/g, '');
                if (!digits) return '';
                let normalized = digits;
                if (normalized.startsWith('8')) {
                    normalized = '7' + normalized.slice(1);
                }
                if (normalized.length === 10 && !normalized.startsWith('7')) {
                    normalized = '7' + normalized;
                }
                return normalized;
            }

            function formatPhoneDisplay(value) {
                if (window.nikaFormatPhoneDisplay) return window.nikaFormatPhoneDisplay(value);
                const digits = normalizePhoneClient(value);
                if (digits.length === 11 && digits.startsWith('7')) {
                    return `+${digits[0]}(${digits.slice(1,4)})${digits.slice(4,7)}-${digits.slice(7,9)}-${digits.slice(9)}`;
                }
                return value;
            }

            function maskPhoneInput(value) {
                if (window.nikaMaskPhoneInput) return window.nikaMaskPhoneInput(value);
                const digits = normalizePhoneClient(value);
                if (!digits) return '';
                let masked = '+';
                masked += digits[0] || '';
                if (digits.length > 1) masked += `(${digits.slice(1,4)}`;
                if (digits.length >= 4) masked += ')';
                if (digits.length >= 5) masked += digits.slice(4,7);
                if (digits.length >= 7) masked += '-' + digits.slice(7,9);
                if (digits.length >= 9) masked += '-' + digits.slice(9,11);
                return masked;
            }

            // Форматируем телефон при загрузке страницы
            const initialPhone = editPhoneInput.value;
            if (initialPhone) {
                const formatted = formatPhoneDisplay(initialPhone);
                if (formatted !== initialPhone) {
                    editPhoneInput.value = formatted;
                }
            }

            // Добавляем маску при вводе
            editPhoneInput.addEventListener('input', (e) => {
                const cursor = editPhoneInput.selectionStart;
                const masked = maskPhoneInput(e.target.value);
                editPhoneInput.value = masked;
                const normalized = normalizePhoneClient(masked);
                editPhoneInput.dataset.normalized = normalized;
                
                // Восстанавливаем позицию курсора
                let newCursor = cursor;
                if (masked.length > e.target.value.length) {
                    newCursor = Math.min(cursor + 1, masked.length);
                } else if (masked.length < e.target.value.length) {
                    newCursor = Math.max(cursor - 1, 0);
                }
                editPhoneInput.setSelectionRange(newCursor, newCursor);
            });

            // При отправке формы нормализуем телефон
            const editOrderForm = document.querySelector('form[action*="order"]');
            if (editOrderForm) {
                editOrderForm.addEventListener('submit', (e) => {
                    const normalized = normalizePhoneClient(editPhoneInput.value);
                    if (normalized && normalized.length === 11) {
                        // Создаем скрытое поле с нормализованным телефоном или обновляем значение
                        let hiddenPhoneInput = document.querySelector('input[name="phone"][type="hidden"]');
                        if (!hiddenPhoneInput) {
                            hiddenPhoneInput = document.createElement('input');
                            hiddenPhoneInput.type = 'hidden';
                            hiddenPhoneInput.name = 'phone_normalized';
                            editOrderForm.appendChild(hiddenPhoneInput);
                        }
                        hiddenPhoneInput.value = normalized;
                        // Также обновляем видимое поле для отправки
                        editPhoneInput.value = normalized;
                    }
                    
                    // Показываем уведомление о сохранении
                    showToast('Сохранение изменений...', 'info', null, 2000);
                });
            }
        }

        // Обработка услуг, запчастей и оплат
        const orderId = ORDER_ID;
        
        // Сохранение услуги (инициализация при загрузке DOM)
        whenDOMReady(function() {
            const saveServiceBtn = document.getElementById('saveServiceBtn');
            if (saveServiceBtn) {
                saveServiceBtn.addEventListener('click', async function() {
                const serviceId = parseInt(document.getElementById('serviceSelect').value);
                const quantity = parseInt(document.getElementById('serviceQuantity').value);
                const priceInput = document.getElementById('servicePrice').value;
                const price = priceInput ? parseFloat(priceInput) : null;

                if (!serviceId || quantity <= 0) {
                    showToast('Выберите услугу и укажите количество', 'warning');
                    return;
                }

                try {
                    const response = await fetch(`/api/orders/${orderId}/services`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            service_id: serviceId,
                            quantity: quantity,
                            price: price
                        })
                    });

                    const data = await response.json();

                    if (data.success) {
                        // Обновляем суммы без перезагрузки страницы
                        if (data.order_total !== undefined) {
                            updateOrderTotals(data.order_total, data.order_paid, data.order_debt, data.prepayment || 0, data.overpayment || 0);
                        }
                        
                        showToast('Услуга успешно добавлена', 'success');
                        setTimeout(() => location.reload(), RELOAD_DELAY);
                    } else {
                        showToast(data.error || 'Не удалось добавить услугу', 'error', 'Ошибка');
                    }
                } catch (error) {
                    console.error('Ошибка при добавлении услуги:', error);
                    showToast('Произошла ошибка при добавлении услуги', 'error', 'Ошибка');
                }
                });
            }
        });
        
        // Удаление услуги (capture-phase, чтобы не блокировалось stopPropagation в других обработчиках)
        document.addEventListener('click', async function(e) {
            if (e.target.closest('.delete-service-btn')) {
                e.preventDefault();
                e.stopPropagation();
                const btn = e.target.closest('.delete-service-btn');
                const serviceId = btn.getAttribute('data-service-id');
                
                if (!serviceId) {
                    console.error('Не найден data-service-id');
                    return;
                }

                if (!confirm('Вы уверены, что хотите удалить эту услугу из заявки?')) {
                    return;
                }

                try {
                    const response = await fetch(`/api/order-services/${serviceId}`, {
                        method: 'DELETE',
                        headers: {
                            'Content-Type': 'application/json',
                        }
                    });

                    const data = await response.json();

                    if (data.success) {
                        showToast('Услуга успешно удалена', 'success');
                        setTimeout(() => location.reload(), RELOAD_DELAY);
                    } else {
                        showToast(data.error || 'Не удалось удалить услугу', 'error', 'Ошибка');
                    }
                } catch (error) {
                    console.error('Ошибка при удалении услуги:', error);
                    showToast('Произошла ошибка при удалении услуги', 'error', 'Ошибка');
                }
            }
        }, true);
        
        // Автозаполнение цены услуги при выборе (старое модальное окно)
        const serviceSelect = document.getElementById('serviceSelect');
        const servicePrice = document.getElementById('servicePrice');
        if (serviceSelect && servicePrice) {
            serviceSelect.addEventListener('change', function() {
                const selectedOption = this.options[this.selectedIndex];
                if (selectedOption && selectedOption.dataset.price) {
                    servicePrice.value = parseFloat(selectedOption.dataset.price).toFixed(2);
                } else {
                    servicePrice.value = '';
                }
            });
        }
        
        // ===== НОВОЕ МОДАЛЬНОЕ ОКНО ДОБАВЛЕНИЯ УСЛУГИ/ТОВАРА =====
        let selectedServiceId = null;
        let selectedPartId = null;
        let allServicesData = [];
        async function ensureServicesLoaded() {
            if (Array.isArray(allServicesData) && allServicesData.length) {
                return allServicesData;
            }
            try {
                const response = await fetch('/api/order/' + ORDER_ID + '/service-catalog');
                if (!response.ok) {
                    throw new Error('HTTP ' + response.status);
                }
                const data = await response.json();
                allServicesData = (data && data.services) || [];
                document.querySelectorAll('select.service-select').forEach(function (sel) {
                    const current = sel.value;
                    sel.querySelectorAll('option:not([value=""])').forEach(function (opt) { opt.remove(); });
                    allServicesData.forEach(function (s) {
                        const opt = document.createElement('option');
                        opt.value = s.id;
                        opt.dataset.price = s.price;
                        opt.textContent = s.name + ' - ' + Number(s.price || 0).toFixed(2);
                        sel.appendChild(opt);
                    });
                    if (current) sel.value = current;
                });
                return allServicesData;
            } catch (error) {
                console.error('Ошибка при загрузке услуг:', error);
                if (typeof showToast === 'function') {
                    showToast('Не удалось загрузить список услуг', 'error', 'Ошибка загрузки', 3000);
                }
                allServicesData = [];
                return [];
            }
        }

        let allPartsData = [];
        let partsCategoriesData = [];
        
        // Загрузка категорий товаров
        async function loadPartsCategories() {
            try {
                const response = await fetch('/warehouse/categories');
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                const categories = await response.json();
                partsCategoriesData = categories;
                return categories;
            } catch (error) {
                console.error('Ошибка при загрузке категорий товаров:', error);
                showToast('Не удалось загрузить категории товаров', 'error', 'Ошибка загрузки', 3000);
                return [];
            }
        }
        
        // Загрузка всех товаров
        async function loadAllParts() {
            try {
                const response = await fetch('/api/parts');
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                const parts = await response.json();
                allPartsData = parts;
                return parts;
            } catch (error) {
                console.error('Ошибка при загрузке товаров:', error);
                showToast('Не удалось загрузить список товаров', 'error', 'Ошибка загрузки', 3000);
                return [];
            }
        }
        
        // Группировка услуг по категориям (по первому слову)
        function groupServicesByCategory(services) {
            const categories = {};
            services.forEach(service => {
                const firstWord = service.name.split(' ')[0];
                const category = firstWord || 'Прочее';
                if (!categories[category]) {
                    categories[category] = [];
                }
                categories[category].push(service);
            });
            return categories;
        }
        
        // Рендеринг категорий услуг
        function renderServicesCategories(categories, searchQuery = '') {
            const container = document.getElementById('servicesCategoriesList');
            if (!container) return;
            
            DOMUtils.clear(container);
            
            const filteredCategories = {};
            Object.keys(categories).forEach(catName => {
                const filtered = categories[catName].filter(service => {
                    if (!searchQuery) return true;
                    return service.name.toLowerCase().includes(searchQuery.toLowerCase());
                });
                if (filtered.length > 0) {
                    filteredCategories[catName] = filtered;
                }
            });
            
            if (Object.keys(filteredCategories).length === 0) {
                const emptyDiv = DOMUtils.createElement('div', 'Ничего не найдено', {
                    'class': 'text-center py-4 text-muted'
                });
                container.appendChild(emptyDiv);
                return;
            }
            
            Object.keys(filteredCategories).sort().forEach(catName => {
                const categoryDiv = document.createElement('div');
                categoryDiv.className = 'mb-3';
                
                const categoryHeader = document.createElement('div');
                categoryHeader.className = 'd-flex align-items-center justify-content-between p-2 border rounded';
                categoryHeader.style.cursor = 'pointer';
                categoryHeader.style.background = 'rgba(59, 130, 246, 0.05)';
                const span = DOMUtils.createElement('span', '', {
                    'style': 'font-weight: 600; color: #3b82f6;'
                });
                const icon = DOMUtils.createElement('i', '', {
                    'class': 'fas fa-chevron-right me-2 category-arrow'
                });
                const catNameText = document.createTextNode(catName);
                span.appendChild(icon);
                span.appendChild(catNameText);
                categoryHeader.appendChild(span);
                
                const servicesList = document.createElement('div');
                servicesList.className = 'list-group mt-2';
                servicesList.style.display = 'none';
                
                filteredCategories[catName].forEach(service => {
                    const serviceItem = document.createElement('div');
                    serviceItem.className = 'list-group-item d-flex justify-content-between align-items-center service-item';
                    serviceItem.style.cursor = 'pointer';
                    serviceItem.dataset.serviceId = service.id;
                    serviceItem.dataset.servicePrice = service.price;
                    const nameSpan = DOMUtils.createElement('span', service.name);
                    const priceBadge = DOMUtils.createElement('span', `${parseFloat(service.price).toFixed(2)} ${((window.nikaMoneySymbol && window.nikaMoneySymbol()) || '₽')}`, {
                        'class': 'badge bg-primary'
                    });
                    serviceItem.appendChild(nameSpan);
                    serviceItem.appendChild(priceBadge);
                    
                    serviceItem.addEventListener('click', function() {
                        // Убираем выделение с других элементов
                        document.querySelectorAll('.service-item').forEach(item => {
                            item.style.background = '';
                        });
                        // Выделяем выбранный элемент
                        this.style.background = 'rgba(59, 130, 246, 0.1)';
                        selectedServiceId = service.id;
                        selectedPartId = null;
                    });
                    
                    servicesList.appendChild(serviceItem);
                });
                
                categoryHeader.addEventListener('click', function() {
                    const arrow = this.querySelector('.category-arrow');
                    const isExpanded = servicesList.style.display !== 'none';
                    servicesList.style.display = isExpanded ? 'none' : 'block';
                    arrow.style.transform = isExpanded ? 'rotate(0deg)' : 'rotate(90deg)';
                });
                
                categoryDiv.appendChild(categoryHeader);
                categoryDiv.appendChild(servicesList);
                container.appendChild(categoryDiv);
            });
        }
        
        // Рендеринг категорий товаров
        function renderPartsCategories(categories, parts, searchQuery = '') {
            const container = document.getElementById('partsCategoriesList');
            if (!container) return;
            
            DOMUtils.clear(container);
            
            if (categories.length === 0) {
                DOMUtils.clear(container);
                const emptyDiv = DOMUtils.createElement('div', 'Категории не найдены', {
                    'class': 'text-center py-4 text-muted'
                });
                container.appendChild(emptyDiv);
                return;
            }
            
            categories.forEach(category => {
                const categoryDiv = document.createElement('div');
                categoryDiv.className = 'mb-3';
                
                const categoryHeader = document.createElement('div');
                categoryHeader.className = 'd-flex align-items-center justify-content-between p-2 border rounded';
                categoryHeader.style.cursor = 'pointer';
                categoryHeader.style.background = 'rgba(139, 92, 246, 0.05)';
                const span = DOMUtils.createElement('span', '', {
                    'style': 'font-weight: 600; color: #8b5cf6;'
                });
                const icon = DOMUtils.createElement('i', '', {
                    'class': 'fas fa-chevron-right me-2 category-arrow'
                });
                const catNameText = document.createTextNode(category.name);
                span.appendChild(icon);
                span.appendChild(catNameText);
                categoryHeader.appendChild(span);
                
                const partsList = document.createElement('div');
                partsList.className = 'list-group mt-2';
                partsList.style.display = 'none';
                
                const categoryParts = parts.filter(part => {
                    if (searchQuery && !part.name.toLowerCase().includes(searchQuery.toLowerCase())) {
                        return false;
                    }
                    return part.category_id === category.id || 
                           (category.children && category.children.some(child => child.id === part.category_id));
                });
                
                if (categoryParts.length > 0) {
                    categoryParts.forEach(part => {
                        const partItem = document.createElement('div');
                        partItem.className = 'list-group-item part-item';
                        partItem.style.cursor = 'pointer';
                        partItem.dataset.partId = part.id;
                        const nameSpan = DOMUtils.createElement('span', part.name);
                        partItem.appendChild(nameSpan);
                        
                        partItem.addEventListener('click', function() {
                            document.querySelectorAll('.part-item').forEach(item => {
                                item.style.background = '';
                            });
                            this.style.background = 'rgba(139, 92, 246, 0.1)';
                            selectedPartId = part.id;
                            selectedServiceId = null;
                        });
                        
                        partsList.appendChild(partItem);
                    });
                }
                
                categoryHeader.addEventListener('click', function() {
                    const arrow = this.querySelector('.category-arrow');
                    const isExpanded = partsList.style.display !== 'none';
                    partsList.style.display = isExpanded ? 'none' : 'block';
                    arrow.style.transform = isExpanded ? 'rotate(0deg)' : 'rotate(90deg)';
                });
                
                categoryDiv.appendChild(categoryHeader);
                if (categoryParts.length > 0) {
                    categoryDiv.appendChild(partsList);
                }
                container.appendChild(categoryDiv);
            });
        }
        
        // Инициализация нового модального окна добавления услуги
        const newAddServiceModal = document.getElementById('addServiceModal');
        if (newAddServiceModal) {
            newAddServiceModal.addEventListener('show.bs.modal', async function() {
                selectedServiceId = null;
                selectedPartId = null;
                
                // Загружаем категории товаров и товары
                await loadPartsCategories();
                await loadAllParts();
                await ensureServicesLoaded();
                
                // Группируем услуги по категориям
                const servicesCategories = groupServicesByCategory(allServicesData);
                renderServicesCategories(servicesCategories);
                
                // Рендерим категории товаров
                renderPartsCategories(partsCategoriesData, allPartsData);
                
                // Очищаем поиск
                const searchInput = document.getElementById('serviceSearchInput');
                if (searchInput) searchInput.value = '';
            });
            
            // Поиск в модальном окне
            const serviceSearchInput = document.getElementById('serviceSearchInput');
            if (serviceSearchInput) {
                serviceSearchInput.addEventListener('input', function() {
                    const query = this.value.trim();
                    const activeTab = document.querySelector('#addServiceModal .nav-link.active');
                    
                    if (activeTab && activeTab.id === 'services-tab') {
                        const servicesCategories = groupServicesByCategory(allServicesData);
                        renderServicesCategories(servicesCategories, query);
                    } else {
                        renderPartsCategories(partsCategoriesData, allPartsData, query);
                    }
                });
            }
            
            // Переключение вкладок
            const servicesTab = document.getElementById('services-tab');
            const goodsTab = document.getElementById('goods-tab');
            const addOneTimeBtn = document.getElementById('addOneTimeServiceBtn');
            
            function updateButtonText() {
                if (!addOneTimeBtn) return;
                const activeTab = document.querySelector('#addServiceModal .nav-link.active');
                if (activeTab && activeTab.id === 'goods-tab') {
                    DOMUtils.clear(addOneTimeBtn);
                    const icon1 = DOMUtils.createElement('i', '', {'class': 'fas fa-plus me-1'});
                    const text1 = document.createTextNode('Добавить разовый товар');
                    addOneTimeBtn.appendChild(icon1);
                    addOneTimeBtn.appendChild(text1);
                } else {
                    DOMUtils.clear(addOneTimeBtn);
                    const icon2 = DOMUtils.createElement('i', '', {'class': 'fas fa-plus me-1'});
                    const text2 = document.createTextNode('Добавить разовую услугу');
                    addOneTimeBtn.appendChild(icon2);
                    addOneTimeBtn.appendChild(text2);
                }
            }
            
            if (servicesTab) {
                servicesTab.addEventListener('shown.bs.tab', function() {
                    const query = serviceSearchInput ? serviceSearchInput.value.trim() : '';
                    const servicesCategories = groupServicesByCategory(allServicesData);
                    renderServicesCategories(servicesCategories, query);
                    updateButtonText();
                });
            }
            if (goodsTab) {
                goodsTab.addEventListener('shown.bs.tab', function() {
                    const query = serviceSearchInput ? serviceSearchInput.value.trim() : '';
                    renderPartsCategories(partsCategoriesData, allPartsData, query);
                    updateButtonText();
                });
            }
            
            // Обновляем текст кнопки при открытии модального окна
            newAddServiceModal.addEventListener('show.bs.modal', function() {
                setTimeout(updateButtonText, MODAL_INIT_DELAY);
            });
        }
        
        // Кнопка "Добавить разовую услугу" (старое модальное окно)
        const addOneTimeServiceBtnOld = document.getElementById('addOneTimeServiceBtn');
        if (addOneTimeServiceBtnOld) {
            addOneTimeServiceBtnOld.addEventListener('click', async function() {
                const activeTab = document.querySelector('#addServiceModal .nav-link.active');
                const isServicesTab = activeTab && activeTab.id === 'services-tab';
                
                try {
                    if (isServicesTab && selectedServiceId) {
                        // Добавляем услугу
                        const service = allServicesData.find(s => s.id === selectedServiceId);
                        if (!service) {
                            showToast('Услуга не найдена', 'error');
                            return;
                        }
                        
                        await addItemToOrder('service', selectedServiceId, 1, service.price);
                        showToast('Услуга успешно добавлена', 'success');
                        
                        // Закрываем модальное окно
                        const modal = bootstrap.Modal.getInstance(newAddServiceModal);
                        if (modal) modal.hide();
                        
                        // Перезагружаем страницу для обновления данных
                        setTimeout(() => location.reload(), RELOAD_DELAY);
                    } else if (!isServicesTab && selectedPartId) {
                        // Добавляем товар
                        const part = allPartsData.find(p => p.id === selectedPartId);
                        if (!part) {
                            showToast('Товар не найден', 'error');
                            return;
                        }
                        
                        await addItemToOrder('part', selectedPartId, 1, part.price || part.retail_price);
                        showToast('Товар успешно добавлен', 'success');
                        
                        // Закрываем модальное окно
                        const modal = bootstrap.Modal.getInstance(newAddServiceModal);
                        if (modal) modal.hide();
                        
                        // Перезагружаем страницу для обновления данных
                        setTimeout(() => location.reload(), RELOAD_DELAY);
                    } else {
                        showToast('Выберите услугу или товар', 'warning');
                    }
                } catch (error) {
                    const errorMessage = error.message || 'Произошла ошибка при добавлении';
                    showToast(errorMessage, 'error', 'Ошибка');
                }
            });
        }
        
        // Обработка модального окна предоплаты (инициализация при загрузке DOM)
        whenDOMReady(function() {
            const addPrepaymentModal = document.getElementById('addPrepaymentModal');
            const savePrepaymentBtn = document.getElementById('savePrepaymentBtn');
            if (savePrepaymentBtn) {
                savePrepaymentBtn.addEventListener('click', async function() {
                const method = document.querySelector('input[name="prepaymentMethod"]:checked');
                const amount = parseFloat(document.getElementById('prepaymentAmount').value);
                const comment = document.getElementById('prepaymentComment').value.trim();
                
                if (!method || !amount || amount <= 0) {
                    showToast('Заполните все обязательные поля', 'warning');
                    return;
                }
                
                try {
                    const response = await fetch(`/api/orders/${orderId}/payments`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            amount: amount,
                            payment_type: method.value,
                            comment: comment,
                            kind: 'deposit',
                            idempotency_key: generateIdempotencyKey()
                        })
                    });
                    
                    const data = await response.json();
                    if (data.success) {
                        showToast('Предоплата успешно добавлена', 'success');
                        setTimeout(() => location.reload(), RELOAD_DELAY);
                    } else {
                        showToast(data.error || 'Не удалось добавить предоплату', 'error', 'Ошибка');
                    }
                } catch (error) {
                    console.error('Ошибка при добавлении предоплаты:', error);
                    showToast('Произошла ошибка при добавлении предоплаты', 'error', 'Ошибка');
                }
                });
            }
        });
        
        // Загрузка списка запчастей для выбора
        async function loadPartsForSelect() {
            try {
                const response = await fetch('/api/parts');
                const parts = await response.json();
                const partSelect = document.getElementById('partSelect');
                
                if (partSelect) {
                    DOMUtils.clear(partSelect);
                    const defaultOption = DOMUtils.createOption('', 'Выберите запчасть...');
                    partSelect.appendChild(defaultOption);
                    parts.forEach(part => {
                        const option = document.createElement('option');
                        option.value = part.id;
                        option.textContent = `${part.name}${part.part_number ? ' (' + part.part_number + ')' : ''} - ${part.stock_quantity} шт. - ${parseFloat(part.price).toFixed(2)} ${((window.nikaMoneySymbol && window.nikaMoneySymbol()) || '₽')}`;
                        option.dataset.price = part.price;
                        option.dataset.stock = part.stock_quantity;
                        partSelect.appendChild(option);
                    });
                    
                    // Сбрасываем цену при загрузке новых запчастей
                    const partPrice = document.getElementById('partPrice');
                    if (partPrice) {
                        partPrice.value = '';
                    }
                }
            } catch (error) {
                console.error('Ошибка при загрузке запчастей:', error);
            }
        }
        
        // Автозаполнение цены запчасти при выборе
        const partSelect = document.getElementById('partSelect');
        const partPrice = document.getElementById('partPrice');
        if (partSelect && partPrice) {
            // Обработчик события change работает и с динамически добавленными опциями
            partSelect.addEventListener('change', function() {
                const selectedOption = this.options[this.selectedIndex];
                if (selectedOption && selectedOption.dataset.price) {
                    partPrice.value = parseFloat(selectedOption.dataset.price).toFixed(2);
                } else {
                    partPrice.value = '';
                }
            });
        }
        
        // Загружаем запчасти при открытии модального окна
        const addPartModal = document.getElementById('addPartModal');
        if (addPartModal) {
            addPartModal.addEventListener('show.bs.modal', function() {
                loadPartsForSelect();
            });
        }
        
        // Сохранение запчасти (инициализация при загрузке DOM)
        whenDOMReady(function() {
            const savePartBtn = document.getElementById('savePartBtn');
            if (savePartBtn) {
                savePartBtn.addEventListener('click', async function() {
                const partId = parseInt(document.getElementById('partSelect').value);
                const quantity = parseInt(document.getElementById('partQuantity').value);
                const priceInput = document.getElementById('partPrice').value;
                const price = priceInput ? parseFloat(priceInput) : null;

                if (!partId || quantity <= 0) {
                    showToast('Выберите запчасть и укажите количество', 'warning');
                    return;
                }

                try {
                    const response = await fetch(`/api/orders/${orderId}/parts`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            part_id: partId,
                            quantity: quantity,
                            price: price
                        })
                    });

                    const data = await response.json();

                    if (data.success) {
                        // Обновляем суммы без перезагрузки страницы
                        if (data.order_total !== undefined) {
                            updateOrderTotals(data.order_total, data.order_paid, data.order_debt, data.prepayment || 0, data.overpayment || 0);
                        }
                        
                        showToast('Запчасть успешно добавлена', 'success');
                        setTimeout(() => location.reload(), RELOAD_DELAY);
                    } else {
                        showToast(data.error || 'Не удалось добавить запчасть', 'error', 'Ошибка');
                    }
                } catch (error) {
                    console.error('Ошибка при добавлении запчасти:', error);
                    showToast('Произошла ошибка при добавлении запчасти', 'error', 'Ошибка');
                }
                });
            }
        });

        // Удаление запчасти (capture-phase)
        document.addEventListener('click', async function(e) {
            if (e.target.closest('.delete-part-btn')) {
                e.preventDefault();
                e.stopPropagation();
                const btn = e.target.closest('.delete-part-btn');
                const partId = btn.getAttribute('data-part-id');
                
                if (!partId) {
                    console.error('Не найден data-part-id');
                    return;
                }

                if (!confirm('Вы уверены, что хотите удалить эту запчасть из заявки? Запчасть будет возвращена на склад.')) {
                    return;
                }

                try {
                    const response = await fetch(`/api/order-parts/${partId}`, {
                        method: 'DELETE',
                        headers: {
                            'Content-Type': 'application/json',
                        }
                    });

                    const data = await response.json();

                    if (data.success) {
                        showToast('Запчасть успешно удалена', 'success');
                        setTimeout(() => location.reload(), RELOAD_DELAY);
                    } else {
                        showToast(data.error || 'Не удалось удалить запчасть', 'error', 'Ошибка');
                    }
                } catch (error) {
                    console.error('Ошибка при удалении запчасти:', error);
                    showToast('Произошла ошибка при удалении запчасти', 'error', 'Ошибка');
                }
            }
        }, true);

        // Редактирование позиций (Товары и услуги) в заявке через правую панель
        (function initOrderItemsSidebarEditor() {
            const sidebar = document.getElementById('orderItemsSidebar');
            if (!sidebar) return;

            const titleEl = document.getElementById('orderItemsSidebarTitle');
            const metaEl = document.getElementById('orderItemsSidebarMeta');
            const closeBtn = document.getElementById('closeOrderItemsSidebarBtn');
            const cancelBtn = document.getElementById('cancelOrderItemChangesBtn');
            const saveBtn = document.getElementById('saveOrderItemChangesBtn');

            const idEl = document.getElementById('orderItemEditId');
            const typeEl = document.getElementById('orderItemEditType');
            const qtyEl = document.getElementById('orderItemEditQty');
            const priceEl = document.getElementById('orderItemEditPrice');
            const costEl = document.getElementById('orderItemEditCost');
            const warrantyEl = document.getElementById('orderItemEditWarranty');
            const discountValEl = document.getElementById('orderItemEditDiscountValue');
            const execEl = document.getElementById('orderItemEditExecutor');
            const btnPct = document.getElementById('orderItemDiscountPercentBtn');
            const btnRub = document.getElementById('orderItemDiscountRubBtn');

            let discountTypeLocal = 'percent';

            function setSidebarActive(active) {
                sidebar.classList.toggle('active', !!active);
            }

            function renderDiscountButtons() {
                if (!btnPct || !btnRub) return;
                btnPct.classList.toggle('active', discountTypeLocal === 'percent');
                btnRub.classList.toggle('active', discountTypeLocal === 'amount');
            }

            if (btnPct && !btnPct.dataset.bound) {
                btnPct.dataset.bound = '1';
                btnPct.addEventListener('click', () => {
                    discountTypeLocal = 'percent';
                    renderDiscountButtons();
                });
            }
            if (btnRub && !btnRub.dataset.bound) {
                btnRub.dataset.bound = '1';
                btnRub.addEventListener('click', () => {
                    discountTypeLocal = 'amount';
                    renderDiscountButtons();
                });
            }

            function openFromItem(itemEl) {
                const t = itemEl.dataset.orderItemType;
                const id = itemEl.dataset.orderItemId;
                if (!t || !id) return;

                const name = itemEl.dataset.itemTitle || '—';
                const qty = itemEl.dataset.itemQuantity || '1';
                const price = itemEl.dataset.itemPrice || '';
                const cost = itemEl.dataset.itemCostPrice || '';
                const warranty = itemEl.dataset.itemWarrantyDays || '';
                const dType = itemEl.dataset.itemDiscountType || '';
                const dVal = itemEl.dataset.itemDiscountValue || '';
                const execId = itemEl.dataset.itemExecutorId || '';

                if (idEl) idEl.value = id;
                if (typeEl) typeEl.value = t;
                if (qtyEl) qtyEl.value = String(qty || 1);
                if (priceEl) priceEl.value = price !== '' ? Number(price || 0).toFixed(2) : '';
                if (costEl) costEl.value = cost !== '' ? String(cost) : '';
                if (warrantyEl) warrantyEl.value = warranty !== '' ? String(warranty) : '';
                if (discountValEl) discountValEl.value = dVal !== '' ? String(dVal) : '';
                if (execEl) execEl.value = execId !== '' ? String(execId) : '';

                if (dType) {
                    const norm = String(dType).toLowerCase();
                    discountTypeLocal = (norm === 'amount' || norm === 'rub' || norm === '₽') ? 'amount' : 'percent';
                } else {
                    discountTypeLocal = 'percent';
                }
                renderDiscountButtons();

                if (titleEl) titleEl.textContent = name;
                if (metaEl) metaEl.textContent = (t === 'service' ? 'Услуга' : 'Товар');

                setSidebarActive(true);
            }

            function closeSidebar() {
                setSidebarActive(false);
            }

            if (closeBtn) closeBtn.addEventListener('click', closeSidebar);
            if (cancelBtn) cancelBtn.addEventListener('click', closeSidebar);

            // Открытие по клику на позицию в списке (кроме кнопок удаления). Запрет для закрытой заявки.
            document.addEventListener('click', (e) => {
                if (e.target.closest('.delete-service-btn') || e.target.closest('.delete-part-btn')) return;
                const itemEl = e.target.closest('.items-list-item');
                if (!itemEl) return;
                if (!itemEl.closest('#itemsListContainer')) return;
                if (window.NIKA_ORDER_PAGE && window.NIKA_ORDER_PAGE.blocksEdit) {
                showToast('Редактирование заблокировано для ' + ((window.NIKA_ORDER_PAGE && window.NIKA_ORDER_PAGE.isFinal) ? 'закрытой заявки' : 'этого статуса'), 'warning', 'Редактирование');
                return;
                }
                openFromItem(itemEl);
            }, true);

            if (saveBtn) {
                saveBtn.addEventListener('click', async () => {
                    const id = idEl?.value;
                    const t = typeEl?.value;
                    if (!id || !t) return;

                    const qty = parseInt(qtyEl?.value || '1', 10);
                    if (!qty || qty < 1) { showToast('Количество должно быть >= 1', 'warning'); return; }

                    const priceRaw = (priceEl?.value || '').toString().replace(',', '.').trim();
                    const price = priceRaw === '' ? null : parseFloat(priceRaw);
                    if (price !== null && (isNaN(price) || price < 0)) { showToast('Некорректная цена', 'warning'); return; }

                    const costRaw = (costEl?.value || '').toString().replace(',', '.').trim();
                    const cost = costRaw === '' ? null : parseFloat(costRaw);
                    if (cost !== null && (isNaN(cost) || cost < 0)) { showToast('Некорректная себестоимость', 'warning'); return; }

                    const warrantyRaw = (warrantyEl?.value || '').toString().trim();
                    const warrantyDays = warrantyRaw === '' ? null : parseInt(warrantyRaw, 10);
                    if (warrantyDays !== null && (isNaN(warrantyDays) || warrantyDays < 0)) { showToast('Некорректная гарантия', 'warning'); return; }

                    const dvRaw = (discountValEl?.value || '').toString().replace(',', '.').trim();
                    const discountValue = dvRaw === '' ? null : parseFloat(dvRaw);
                    if (discountValue !== null && (isNaN(discountValue) || discountValue < 0)) { showToast('Некорректная скидка', 'warning'); return; }
                    const discountType = discountValue === null ? null : discountTypeLocal;

                    const execRaw = (execEl?.value || '').toString().trim();
                    const executorId = execRaw === '' ? null : parseInt(execRaw, 10);

                    const payload = {
                        quantity: qty,
                        price,
                        warranty_days: warrantyDays,
                        discount_type: discountType,
                        discount_value: discountValue,
                        executor_id: executorId
                    };
                    if (t === 'service') payload.cost_price = cost;
                    if (t === 'part') payload.purchase_price = cost;

                    try {
                        const endpoint = t === 'service' ? `/api/order-services/${id}` : `/api/order-parts/${id}`;
                        const resp = await fetch(endpoint, {
                            method: 'PATCH',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify(payload)
                        });
                        const data = await resp.json();
                        if (!data.success) {
                            showToast(data.error || 'Не удалось сохранить', 'error', 'Ошибка');
                            return;
                        }
                        showToast('Сохранено', 'success');
                        setTimeout(() => location.reload(), 300);
                    } catch (err) {
                        console.error(err);
                        showToast('Ошибка при сохранении', 'error', 'Ошибка');
                    }
                });
            }
        })();

        // Обработка оплат (инициализация при загрузке DOM)
        whenDOMReady(function() {
            const createInvoiceSubmit = document.getElementById('createInvoiceSubmit');
            if (createInvoiceSubmit) {
                createInvoiceSubmit.addEventListener('click', async function() {
                    const errEl = document.getElementById('createInvoiceError');
                    if (errEl) errEl.textContent = '';
                    const serviceIds = [...document.querySelectorAll('.invoice-svc:checked')].map(el => parseInt(el.value, 10));
                    const partIds = [...document.querySelectorAll('.invoice-part:checked')].map(el => parseInt(el.value, 10));
                    const csrf = document.querySelector('meta[name="csrf-token"]')?.content
                        || document.querySelector('input[name="csrf_token"]')?.value || '';
                    createInvoiceSubmit.disabled = true;
                    try {
                        const invoiceOrderId = numericOrderId();
                        if (!invoiceOrderId) {
                            showToast('Не удалось определить заявку', 'error');
                            createInvoiceSubmit.disabled = false;
                            return;
                        }
                        const resp = await fetch(`/invoices/api/from-order/${invoiceOrderId}`, {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json', 'X-CSRFToken': csrf},
                            body: JSON.stringify({
                                service_ids: serviceIds,
                                part_ids: partIds,
                                due_date: document.getElementById('invoiceDueDate')?.value || null,
                                comment: document.getElementById('invoiceComment')?.value || null
                            })
                        });
                        const data = await resp.json();
                        if (!data.success) {
                            if (errEl) errEl.textContent = data.error || 'Ошибка создания счёта';
                            else showToast(data.error || 'Ошибка создания счёта', 'error');
                            createInvoiceSubmit.disabled = false;
                            return;
                        }
                        if (data.url) window.location.href = data.url;
                        else window.location.reload();
                    } catch (e) {
                        if (errEl) errEl.textContent = 'Ошибка сети';
                        createInvoiceSubmit.disabled = false;
                    }
                });
            }

            const addPaymentModal = document.getElementById('addPaymentModal');
            const addPaymentForm = document.getElementById('addPaymentForm');
            const savePaymentBtn = document.getElementById('savePaymentBtn');

            // Сохранение оплаты
            if (savePaymentBtn) {
                savePaymentBtn.addEventListener('click', async function() {
                const amount = parseFloat(document.getElementById('paymentAmount').value);
                const paymentType = document.getElementById('paymentType').value;
                const comment = document.getElementById('paymentComment').value.trim();
                
                // Получаем текущий долг
                const debtEl = document.getElementById('paymentOrderDebt');
                let maxDebt = 0;
                if (debtEl) {
                    const debtText = debtEl.textContent.replace(/[^\d.,]/g, '').replace(',', '.');
                    maxDebt = parseFloat(debtText) || 0;
                }

                if (!amount || amount <= 0) {
                    showToast('Введите корректную сумму оплаты', 'warning');
                    return;
                }
                
                // Проверяем, что сумма не превышает долг
                if (maxDebt > 0 && amount > maxDebt) {
                    showToast(`Сумма оплаты не может превышать долг (${maxDebt.toFixed(2)} ${((window.nikaMoneySymbol && window.nikaMoneySymbol()) || '₽')})`, 'warning');
                    return;
                }

                try {
                    const response = await fetch(`/api/orders/${orderId}/payments`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            amount: amount,
                            payment_type: paymentType,
                            comment: comment,
                            kind: 'payment',
                            idempotency_key: generateIdempotencyKey()
                        })
                    });

                    const data = await response.json();

                    if (data.success) {
                        // Обновляем список оплат
                        updatePaymentsList(data.payments, data.order_total, data.order_paid, data.order_debt, data.prepayment || 0, data.overpayment || 0);
                        
                        // Закрываем модальное окно и очищаем форму
                        const modal = bootstrap.Modal.getInstance(addPaymentModal);
                        modal.hide();
                        addPaymentForm.reset();
                        
                        showToast('Оплата успешно добавлена', 'success');
                        if (pendingClosedPrintAfterPayment) {
                            pendingClosedPrintAfterPayment = false;
                            setTimeout(() => {
                                handleClosedPrintFlow();
                                scheduleReloadAfterPrintFlow(RELOAD_DELAY);
                            }, 150);
                        } else {
                            // Перезагрузка без open_payment_modal — иначе модалка откроется повторно
                            setTimeout(() => reloadOrderDetailClean(), RELOAD_DELAY);
                        }
                    } else {
                        showToast(data.error || 'Не удалось добавить оплату', 'error', 'Ошибка');
                    }
                } catch (error) {
                    console.error('Ошибка при добавлении оплаты:', error);
                    showToast('Произошла ошибка при добавлении оплаты', 'error', 'Ошибка');
                }
                });
            }

        });
        
        // Функция для открытия модалки оплаты с информацией о долге
        function openPaymentModalWithDebt() {
            const addPaymentModal = document.getElementById('addPaymentModal');
            if (!addPaymentModal) return false;
            
            // Получаем актуальные данные о долге из DOM
            const orderTotalEl = document.querySelector('[data-order-total]');
            const orderPaidEl = document.querySelector('[data-order-paid]');
            const orderDebtEl = document.querySelector('[data-order-debt]');
            
            let orderTotal = Number(window.NIKA_ORDER_PAGE && window.NIKA_ORDER_PAGE.orderTotal) || 0;
            let orderPaid = Number(window.NIKA_ORDER_PAGE && window.NIKA_ORDER_PAGE.orderPaid) || 0;
            let orderDebt = Number(window.NIKA_ORDER_PAGE && window.NIKA_ORDER_PAGE.orderDebt) || 0;
            
            // Пытаемся получить актуальные значения из DOM
            if (orderTotalEl) {
                const totalText = orderTotalEl.textContent.replace(/[^\d.,]/g, '').replace(',', '.');
                orderTotal = parseFloat(totalText) || orderTotal;
            }
            if (orderPaidEl) {
                const paidText = orderPaidEl.textContent.replace(/[^\d.,]/g, '').replace(',', '.');
                orderPaid = parseFloat(paidText) || orderPaid;
            }
            if (orderDebtEl) {
                const debtValue = orderDebtEl.getAttribute('data-order-debt-value');
                if (debtValue !== null && debtValue !== '') {
                    orderDebt = parseFloat(debtValue) || orderDebt;
                } else {
                    const debtText = orderDebtEl.textContent.replace(/[^\d.,]/g, '').replace(',', '.');
                    orderDebt = parseFloat(debtText) || orderDebt;
                }
            }

            if (orderDebt <= 0) {
                showToast('Долг отсутствует', 'info', null, 3000);
                return false;
            }
            
            // Обновляем информацию в модалке
            const totalEl = document.getElementById('paymentOrderTotal');
            const paidEl = document.getElementById('paymentOrderPaid');
            const debtEl = document.getElementById('paymentOrderDebt');
            const amountInput = document.getElementById('paymentAmount');
            const amountHelp = document.getElementById('paymentAmountHelp');
            
            if (totalEl) totalEl.textContent = orderTotal.toFixed(2) + ' ' + ((window.nikaMoneySymbol && window.nikaMoneySymbol()) || '₽');
            if (paidEl) paidEl.textContent = orderPaid.toFixed(2) + ' ' + ((window.nikaMoneySymbol && window.nikaMoneySymbol()) || '₽');
            if (debtEl) {
                debtEl.textContent = orderDebt.toFixed(2) + ' ' + ((window.nikaMoneySymbol && window.nikaMoneySymbol()) || '₽');
                debtEl.className = orderDebt > 0 ? 'text-danger fw-bold' : 'text-success fw-bold';
            }
            
            if (amountInput) {
                amountInput.value = orderDebt > 0 ? orderDebt.toFixed(2) : '';
                amountInput.max = orderDebt > 0 ? orderDebt.toFixed(2) : '';
                amountInput.min = '0.01';
            }
            
            if (amountHelp) {
                if (orderDebt > 0) {
                    amountHelp.textContent = 'Максимальная сумма: ' + orderDebt.toFixed(2) + ' ' + ((window.nikaMoneySymbol && window.nikaMoneySymbol()) || '₽');
                    amountHelp.className = 'form-text text-muted';
                } else {
                    amountHelp.textContent = 'Долг отсутствует';
                    amountHelp.className = 'form-text text-success';
                }
            }
            
            // Разрешаем открытие (для потока закрытия заявки с долгом)
            window._paymentModalFromCloseFlow = true;
            const modal = new bootstrap.Modal(addPaymentModal);
            modal.show();
            return true;
        }
        
        // Глобальная функция для вызова из других мест
        window.openPaymentModal = openPaymentModalWithDebt;

        // При открытии из /all_orders с флагом — показать модалку оплаты после загрузки
        document.addEventListener('DOMContentLoaded', function() {
            const params = new URLSearchParams(window.location.search);
            if (params.get('open_payment_modal') === '1') {
                // Сразу убираем флаг: иначе после оплаты reload снова откроет модалку
                stripOpenPaymentModalFromUrl();
                setTimeout(function() {
                    if (openPaymentModalWithDebt()) {
                        // Как при закрытии с карточки: после оплаты — выбор печати
                        pendingClosedPrintAfterPayment = true;
                    }
                }, 500);
            }
        });

        // Удаление оплат ЗАПРЕЩЕНО - используйте только возврат (refund)

        // ===== ОБЪЕДИНЕННАЯ ПРОДАЖА =====
        let serviceRowIndex = 1;
        let partRowIndex = 1;

        // Загрузка запчастей для объединенной формы
        async function loadPartsForUnifiedForm() {
            try {
                const response = await fetch('/api/parts');
                const parts = await response.json();
                const partSelects = document.querySelectorAll('#unifiedSellModal .part-select');
                
                partSelects.forEach(select => {
                    DOMUtils.clear(select);
                    const defaultOption = DOMUtils.createOption('', 'Выберите запчасть...');
                    select.appendChild(defaultOption);
                    parts.forEach(part => {
                        const option = document.createElement('option');
                        option.value = part.id;
                        option.textContent = `${part.name}${part.part_number ? ' (' + part.part_number + ')' : ''} - ${part.stock_quantity} шт. - ${parseFloat(part.price || part.retail_price || 0).toFixed(2)} ${((window.nikaMoneySymbol && window.nikaMoneySymbol()) || '₽')}`;
                        option.dataset.price = part.price || part.retail_price || 0;
                        option.dataset.stock = part.stock_quantity;
                        select.appendChild(option);
                    });
                });
            } catch (error) {
                console.error('Ошибка при загрузке запчастей:', error);
            }
        }

        // Загрузка запчастей при открытии модального окна
        const unifiedSellModal = document.getElementById('unifiedSellModal');
        if (unifiedSellModal) {
            unifiedSellModal.addEventListener('show.bs.modal', function() {
                loadPartsForUnifiedForm();
                serviceRowIndex = 1;
                partRowIndex = 1;
                // Очищаем поле поиска
                const searchInput = document.getElementById('unifiedSearchInput');
                if (searchInput) searchInput.value = '';
                const searchResults = document.getElementById('unifiedSearchResults');
                if (searchResults) searchResults.style.display = 'none';
            });
        }

        // Единый поиск по услугам и товарам
        const unifiedSearchInput = document.getElementById('unifiedSearchInput');
        const unifiedSearchResults = document.getElementById('unifiedSearchResults');
        let searchTimeout = null;

        if (unifiedSearchInput && unifiedSearchResults) {
            unifiedSearchInput.addEventListener('input', function() {
                const query = this.value.trim();
                
                if (searchTimeout) clearTimeout(searchTimeout);
                
                if (query.length < 1) {
                    unifiedSearchResults.style.display = 'none';
                    return;
                }
                
                searchTimeout = setTimeout(async () => {
                    try {
                        const response = await fetch(`/api/search/items?q=${encodeURIComponent(query)}`);
                        const data = await response.json();
                        
                        if (data.success && data.items.length > 0) {
                            let html = '';
                            data.items.forEach(item => {
                                const stockInfo = item.stock !== null ? `<small class="text-muted">(${item.stock} шт.)</small>` : '';
                                const typeLabel = item.type === 'service' ? '<span class="badge bg-primary me-1">Услуга</span>' : '<span class="badge bg-secondary me-1">Товар</span>';
                                const priceText = parseFloat(item.price).toFixed(2);
                                
                                html += `
                                    <a href="#" class="list-group-item list-group-item-action unified-search-item"
                                       data-id="${item.id}" data-type="${item.type}" data-name="${item.name}" 
                                       data-price="${item.price}" data-stock="${item.stock || 0}">
                                        <div class="d-flex justify-content-between align-items-center">
                                            <div>
                                                ${typeLabel}
                                                <strong>${item.name}</strong>
                                                ${stockInfo}
                                            </div>
                                            <div class="text-success fw-bold">${priceText} ${((window.nikaMoneySymbol && window.nikaMoneySymbol()) || '₽')}</div>
                                        </div>
                                    </a>
                                `;
                            });
                            DOMUtils.setSafeHTML(unifiedSearchResults, html);
                            unifiedSearchResults.style.display = 'block';
                            
                            // Добавляем обработчики кликов
                            document.querySelectorAll('.unified-search-item').forEach(item => {
                                item.addEventListener('click', function(e) {
                                    e.preventDefault();
                                    const itemId = this.dataset.id;
                                    const itemType = this.dataset.type;
                                    const itemName = this.dataset.name;
                                    const itemPrice = this.dataset.price;
                                    
                                    if (itemType === 'service') {
                                        // Добавляем услугу в первый пустой слот или создаём новый
                                        const emptyServiceSelect = document.querySelector('.service-select[data-index="0"]');
                                        if (emptyServiceSelect && !emptyServiceSelect.value) {
                                            emptyServiceSelect.value = itemId;
                                            const priceInput = document.querySelector('.service-price[data-index="0"]');
                                            if (priceInput) priceInput.value = itemPrice;
                                        } else {
                                            // Клик на "Добавить услугу" и затем заполняем
                                            addServiceRowBtn.click();
                                            setTimeout(() => {
                                                const lastSelect = document.querySelector(`.service-select[data-index="${serviceRowIndex - 1}"]`);
                                                if (lastSelect) lastSelect.value = itemId;
                                                const lastPrice = document.querySelector(`.service-price[data-index="${serviceRowIndex - 1}"]`);
                                                if (lastPrice) lastPrice.value = itemPrice;
                                            }, 50);
                                        }
                                    } else {
                                        // Добавляем товар
                                        const emptyPartSelect = document.querySelector('.part-select[data-index="0"]');
                                        if (emptyPartSelect && !emptyPartSelect.value) {
                                            // Добавляем опцию если не существует
                                            let option = emptyPartSelect.querySelector(`option[value="${itemId}"]`);
                                            if (!option) {
                                                option = document.createElement('option');
                                                option.value = itemId;
                                                option.textContent = `${itemName} - ${itemPrice} ${((window.nikaMoneySymbol && window.nikaMoneySymbol()) || '₽')}`;
                                                option.dataset.price = itemPrice;
                                                emptyPartSelect.appendChild(option);
                                            }
                                            emptyPartSelect.value = itemId;
                                            const priceInput = document.querySelector('.part-price[data-index="0"]');
                                            if (priceInput) priceInput.value = itemPrice;
                                        } else {
                                            addPartRowBtn.click();
                                            setTimeout(() => {
                                                const lastSelect = document.querySelector(`.part-select[data-index="${partRowIndex - 1}"]`);
                                                if (lastSelect) {
                                                    let option = lastSelect.querySelector(`option[value="${itemId}"]`);
                                                    if (!option) {
                                                        option = document.createElement('option');
                                                        option.value = itemId;
                                                        option.textContent = `${itemName} - ${itemPrice} ${((window.nikaMoneySymbol && window.nikaMoneySymbol()) || '₽')}`;
                                                        option.dataset.price = itemPrice;
                                                        lastSelect.appendChild(option);
                                                    }
                                                    lastSelect.value = itemId;
                                                }
                                                const lastPrice = document.querySelector(`.part-price[data-index="${partRowIndex - 1}"]`);
                                                if (lastPrice) lastPrice.value = itemPrice;
                                            }, 50);
                                        }
                                    }
                                    
                                    // Очищаем поиск
                                    unifiedSearchInput.value = '';
                                    unifiedSearchResults.style.display = 'none';
                                });
                            });
                        } else {
                            DOMUtils.clear(unifiedSearchResults);
                            const notFoundDiv = DOMUtils.createElement('div', 'Ничего не найдено', {
                                'class': 'list-group-item text-muted'
                            });
                            unifiedSearchResults.appendChild(notFoundDiv);
                            unifiedSearchResults.style.display = 'block';
                        }
                    } catch (error) {
                        console.error('Ошибка поиска:', error);
                    }
                }, 300);
            });
            
            // Скрываем результаты при клике вне
            document.addEventListener('click', function(e) {
                if (!unifiedSearchInput.contains(e.target) && !unifiedSearchResults.contains(e.target)) {
                    unifiedSearchResults.style.display = 'none';
                }
            });
        }

        // Добавление строки услуги
        const addServiceRowBtn = document.getElementById('addServiceRowBtn');
        if (addServiceRowBtn) {
            addServiceRowBtn.addEventListener('click', function() {
                const container = document.getElementById('servicesContainer');
                // ВАЖНО: не вставляем значения названий услуг внутрь JS template string,
                // иначе названия с обратным слешем (например "PS4\\Xbox") ломают парсер (SyntaxError).
                // Вместо этого копируем options из первой строки (она уже отрендерена в DOM).
                const baseSelect = container ? container.querySelector('.service-select') : null;
                const newRow = document.createElement('div');
                newRow.className = 'service-item mb-3 p-3 border rounded';
                const serviceRowHTML = `
                    <div class="row">
                        <div class="col-md-5">
                            <label class="form-label">Услуга</label>
                            <select class="form-select service-select" data-index="${serviceRowIndex}">
                                <option value="">Выберите услугу...</option>
                            </select>
                        </div>
                        <div class="col-md-2">
                            <label class="form-label">Кол-во</label>
                            <input type="number" class="form-control service-quantity" min="1" value="1" data-index="${serviceRowIndex}">
                        </div>
                        <div class="col-md-3">
                            <label class="form-label">Цена (₽)</label>
                            <input type="number" class="form-control service-price" step="0.01" min="0" placeholder="Авто" data-index="${serviceRowIndex}">
                        </div>
                        <div class="col-md-2 d-flex align-items-end">
                            <button type="button" class="btn btn-sm btn-danger remove-service-btn" data-index="${serviceRowIndex}">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                    </div>
                `;
                DOMUtils.setSafeHTML(newRow, serviceRowHTML, true);
                container.appendChild(newRow);
                
                // Обработчик автозаполнения цены
                const select = newRow.querySelector('.service-select');
                const priceInput = newRow.querySelector('.service-price');
                // Заполняем options из первой строки (если она есть)
                if (select && baseSelect) {
                    select.innerHTML = baseSelect.innerHTML;
                }
                select.addEventListener('change', function() {
                    const selectedOption = this.options[this.selectedIndex];
                    if (selectedOption && selectedOption.dataset.price) {
                        priceInput.value = parseFloat(selectedOption.dataset.price).toFixed(2);
                    } else {
                        priceInput.value = '';
                    }
                });
                
                // Обработчик удаления строки
                const removeBtn = newRow.querySelector('.remove-service-btn');
                removeBtn.addEventListener('click', function() {
                    newRow.remove();
                });
                
                serviceRowIndex++;
            });
        }

        // Добавление строки запчасти
        const addPartRowBtn = document.getElementById('addPartRowBtn');
        if (addPartRowBtn) {
            addPartRowBtn.addEventListener('click', async function() {
                const container = document.getElementById('partsContainer');
                const newRow = document.createElement('div');
                newRow.className = 'part-item mb-3 p-3 border rounded';
                // HTML генерируется статически, поэтому безопасен
                const partRowHTML = `
                    <div class="row">
                        <div class="col-md-5">
                            <label class="form-label">Запчасть</label>
                            <select class="form-select part-select" data-index="${partRowIndex}">
                                <option value="">Выберите запчасть...</option>
                            </select>
                        </div>
                        <div class="col-md-2">
                            <label class="form-label">Кол-во</label>
                            <input type="number" class="form-control part-quantity" min="1" value="1" data-index="${partRowIndex}">
                        </div>
                        <div class="col-md-3">
                            <label class="form-label">Цена (₽)</label>
                            <input type="number" class="form-control part-price" step="0.01" min="0" placeholder="Авто" data-index="${partRowIndex}">
                        </div>
                        <div class="col-md-2 d-flex align-items-end">
                            <button type="button" class="btn btn-sm btn-danger remove-part-btn" data-index="${partRowIndex}">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                    </div>
                `;
                DOMUtils.setSafeHTML(newRow, partRowHTML, true);
                container.appendChild(newRow);
                
                // Загружаем запчасти в новый select
                await loadPartsForUnifiedForm();
                
                // Обработчик автозаполнения цены
                const select = newRow.querySelector('.part-select');
                const priceInput = newRow.querySelector('.part-price');
                select.addEventListener('change', function() {
                    const selectedOption = this.options[this.selectedIndex];
                    if (selectedOption && selectedOption.dataset.price) {
                        priceInput.value = parseFloat(selectedOption.dataset.price).toFixed(2);
                    } else {
                        priceInput.value = '';
                    }
                });
                
                // Обработчик удаления строки
                const removeBtn = newRow.querySelector('.remove-part-btn');
                removeBtn.addEventListener('click', function() {
                    newRow.remove();
                });
                
                partRowIndex++;
            });
        }

        // Обработчики автозаполнения для первой строки услуг
        document.addEventListener('DOMContentLoaded', function() {
            const firstServiceSelect = document.querySelector('#servicesContainer .service-select[data-index="0"]');
            const firstServicePrice = document.querySelector('#servicesContainer .service-price[data-index="0"]');
            if (firstServiceSelect && firstServicePrice) {
                firstServiceSelect.addEventListener('change', function() {
                    const selectedOption = this.options[this.selectedIndex];
                    if (selectedOption && selectedOption.dataset.price) {
                        firstServicePrice.value = parseFloat(selectedOption.dataset.price).toFixed(2);
                    } else {
                        firstServicePrice.value = '';
                    }
                });
            }

            // Показываем кнопку удаления для первой строки, если есть несколько строк
            const removeServiceBtns = document.querySelectorAll('.remove-service-btn');
            removeServiceBtns.forEach(btn => {
                if (btn.dataset.index === '0') {
                    btn.style.display = 'none';
                }
            });

            const removePartBtns = document.querySelectorAll('.remove-part-btn');
            removePartBtns.forEach(btn => {
                if (btn.dataset.index === '0') {
                    btn.style.display = 'none';
                }
            });
        });

        // Обработчик удаления строк услуг и запчастей
        document.addEventListener('click', function(e) {
            if (e.target.closest('.remove-service-btn')) {
                const btn = e.target.closest('.remove-service-btn');
                const item = btn.closest('.service-item');
                if (item) {
                    item.remove();
                }
            }
            if (e.target.closest('.remove-part-btn')) {
                const btn = e.target.closest('.remove-part-btn');
                const item = btn.closest('.part-item');
                if (item) {
                    item.remove();
                }
            }
        });

        // Сохранение объединенной продажи
        const saveUnifiedSellBtn = document.getElementById('saveUnifiedSellBtn');
        if (saveUnifiedSellBtn) {
            saveUnifiedSellBtn.addEventListener('click', async function() {
                // Собираем услуги
                const services = [];
                const serviceItems = document.querySelectorAll('#servicesContainer .service-item');
                serviceItems.forEach(item => {
                    const select = item.querySelector('.service-select');
                    const quantityInput = item.querySelector('.service-quantity');
                    const priceInput = item.querySelector('.service-price');
                    
                    const serviceId = parseInt(select.value);
                    if (serviceId) {
                        const quantity = parseInt(quantityInput.value) || 1;
                        const price = priceInput.value ? parseFloat(priceInput.value) : null;
                        services.push({
                            service_id: serviceId,
                            quantity: quantity,
                            price: price
                        });
                    }
                });

                // Собираем запчасти
                const parts = [];
                const partItems = document.querySelectorAll('#partsContainer .part-item');
                partItems.forEach(item => {
                    const select = item.querySelector('.part-select');
                    const quantityInput = item.querySelector('.part-quantity');
                    const priceInput = item.querySelector('.part-price');
                    
                    const partId = parseInt(select.value);
                    if (partId) {
                        const quantity = parseInt(quantityInput.value) || 1;
                        const price = priceInput.value ? parseFloat(priceInput.value) : null;
                        parts.push({
                            part_id: partId,
                            quantity: quantity,
                            price: price
                        });
                    }
                });

                // Проверяем, что есть хотя бы одна услуга или запчасть
                if (services.length === 0 && parts.length === 0) {
                    showToast('Добавьте хотя бы одну услугу или запчасть', 'warning');
                    return;
                }

                // Собираем данные об оплате
                const paymentAmount = parseFloat(document.getElementById('unifiedPaymentAmount').value) || 0;
                const paymentType = document.getElementById('unifiedPaymentType').value;
                const paymentComment = document.getElementById('unifiedPaymentComment').value.trim();

                const payment = {};
                if (paymentAmount > 0 && paymentType) {
                    payment.amount = paymentAmount;
                    payment.payment_type = paymentType;
                    if (paymentComment) {
                        payment.comment = paymentComment;
                    }
                }

                try {
                    const response = await fetch(`/api/orders/${orderId}/sell`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            services: services,
                            parts: parts,
                            payment: payment
                        })
                    });

                    const data = await response.json();

                    if (data.success) {
                        // Закрываем модальное окно
                        const modal = bootstrap.Modal.getInstance(unifiedSellModal);
                        modal.hide();
                        
                        showToast('Продажа успешно оформлена', 'success');
                        setTimeout(() => location.reload(), RELOAD_DELAY);
                    } else {
                        showToast(data.error || 'Не удалось оформить продажу', 'error', 'Ошибка');
                    }
                } catch (error) {
                    console.error('Ошибка при оформлении продажи:', error);
                    showToast('Произошла ошибка при оформлении продажи', 'error', 'Ошибка');
                }
            });
        }
        // ===== КОНЕЦ ОБЪЕДИНЕННОЙ ПРОДАЖИ =====

        // ===== ПОИСК/ПРОСМОТР В МОДАЛЬНОМ ОКНЕ "ДОБАВИТЬ ТОВАР ИЛИ УСЛУГУ" =====
        // ВНИМАНИЕ: в этом файле уже есть searchTimeout для объединённой продажи выше,
        // поэтому используем отдельное имя, чтобы не падал весь JS.
        let itemsSearchTimeout = null;
        let selectedItem = null; // Хранит выбранный элемент {id, type, name, price}
        let itemsSearchInitialized = false;
        let itemsBrowseInitialized = false;
        let currentItemsView = 'home'; // home | services | parts | search
        let lastBrowseView = 'home';
        let itemsKeyboardInitialized = false;
        let oneTimeMode = null; // 'service' | 'part' | null
        let discountType = 'percent'; // percent | amount
        let itemsModalDirty = false;
        let itemsAddedNames = [];

        function updateAddedSummaryUI() {
            const el = document.getElementById('itemsAddedSummary');
            if (!el) return;
            if (!itemsAddedNames || !itemsAddedNames.length) {
                el.textContent = '—';
                return;
            }
            const max = 5;
            const shown = itemsAddedNames.slice(-max);
            const extra = itemsAddedNames.length - shown.length;
            el.textContent = shown.join(', ') + (extra > 0 ? ` +${extra}` : '');
        }

        function markItemsAdded(name) {
            itemsModalDirty = true;
            if (name) itemsAddedNames.push(String(name));
            updateAddedSummaryUI();
        }

        function afterSuccessfulItemsAdd() {
            // Сбрасываем выбор, чтобы можно было добавить следующую позицию
            resetItemsSelection();
            const oneTimeForm = document.getElementById('oneTimeForm');
            if (oneTimeForm) oneTimeForm.style.display = 'none';
            oneTimeMode = null;
            const searchInput = document.getElementById('itemsSearchInput');
            if (searchInput) searchInput.focus();
        }

        /**
         * Добавляет строку в список «Товары и услуги» на странице сразу после добавления в модалке.
         * @param {string} type - 'service' | 'part'
         * @param {Object} opts - id (для удаления, опционально), name, quantity, price
         */
        function appendOrderItemToPage(type, opts) {
            const container = document.getElementById('itemsListContainer');
            if (!container) return;
            const name = (opts.name || '').trim() || (type === 'service' ? 'Услуга' : 'Товар');
            const quantity = parseInt(opts.quantity, 10) || 1;
            const price = parseFloat(String(opts.price || 0).replace(',', '.')) || 0;
            const costVal = opts.cost ?? opts.cost_price ?? opts.purchase_price;
            const cost = costVal != null && costVal !== '' ? parseFloat(String(costVal).replace(',', '.')) : null;
            const sum = (quantity * price).toFixed(2);
            const priceStr = price.toFixed(2);
            const id = opts.id != null ? opts.id : null;
            const createdAtStr = opts.created_at ? formatDate(opts.created_at) : formatDate(new Date().toISOString());

            function ensureLists() {
                const placeholder = container.querySelector('.text-center.py-5');
                if (placeholder) {
                    container.innerHTML = '';
                    const svcBlock = document.createElement('div');
                    svcBlock.className = 'mb-3';
                    svcBlock.innerHTML = '<h6 class="mb-2" style="font-size: 0.85rem; font-weight: 600; color: #374151;"><i class="fas fa-cogs me-1" style="color: #3b82f6;"></i>Услуги</h6><div class="list-group list-group-flush" data-items-type="services"></div>';
                    const partsBlock = document.createElement('div');
                    partsBlock.innerHTML = '<h6 class="mb-2" style="font-size: 0.85rem; font-weight: 600; color: #374151;"><i class="fas fa-cog me-1" style="color: #8b5cf6;"></i>Запчасти</h6><div class="list-group list-group-flush" data-items-type="parts"></div>';
                    container.appendChild(svcBlock);
                    container.appendChild(partsBlock);
                }
                const lists = container.querySelectorAll('[data-items-type]');
                const servicesList = Array.from(lists).find(el => el.getAttribute('data-items-type') === 'services');
                const partsList = Array.from(lists).find(el => el.getAttribute('data-items-type') === 'parts');
                if (!servicesList || !partsList) {
                    const h6s = container.querySelectorAll('h6');
                    let sList = null, pList = null;
                    h6s.forEach(h => {
                        const next = h.nextElementSibling;
                        if (next && next.classList.contains('list-group')) {
                            if (h.textContent.indexOf('Услуги') !== -1) sList = next;
                            else if (h.textContent.indexOf('Запчасти') !== -1) pList = next;
                        }
                    });
                    return { servicesList: sList, partsList: pList };
                }
                return { servicesList, partsList };
            }

            const { servicesList, partsList } = ensureLists();
            const list = type === 'service' ? servicesList : partsList;
            if (!list) return;

            const iconColor = type === 'service' ? '#3b82f6' : '#8b5cf6';
            const sumColor = type === 'service' ? '#3b82f6' : '#8b5cf6';
            const item = document.createElement('div');
            item.className = 'list-group-item items-list-item d-flex justify-content-between align-items-center';
            item.setAttribute('data-order-item-type', type);
            if (id != null) item.setAttribute('data-order-item-id', String(id));
            item.setAttribute('data-item-title', name);
            item.setAttribute('data-item-quantity', String(quantity));
            item.setAttribute('data-item-price', String(price));
            item.setAttribute('data-item-cost-price', cost != null && cost > 0 ? String(cost) : '');
            item.setAttribute('data-item-date', createdAtStr);
            item.style.cssText = 'border: none; border-bottom: 1px solid rgba(229, 231, 235, 0.4); padding: 0.75rem 0;';
            const costSpan = (cost != null && cost > 0) ? '<span title="Себестоимость">Себ.: <strong>' + cost.toFixed(2) + ' ' + ((window.nikaMoneySymbol && window.nikaMoneySymbol()) || '₽') + '</strong></span>' : '';
            item.innerHTML = '<div class="flex-grow-1">' +
                '<div class="d-flex align-items-center mb-1 flex-wrap gap-1">' +
                '<div style="width: 24px; height: 24px; background: rgba(59, 130, 246, 0.1); border-radius: 6px; display: flex; align-items: center; justify-content: center; margin-right: 0.5rem;"><i class="fas fa-' + (type === 'service' ? 'cogs' : 'cog') + '" style="color: ' + iconColor + '; font-size: 0.7rem;"></i></div>' +
                '<span style="font-weight: 500; color: #374151; font-size: 0.875rem;">' + escapeHtmlForItems(name) + '</span></div>' +
                '<div class="d-flex align-items-center gap-3" style="font-size: 0.75rem; color: #6b7280;">' +
                '<span>Кол-во: <strong>' + quantity + '</strong></span><span>Цена: <strong>' + priceStr + ' ' + ((window.nikaMoneySymbol && window.nikaMoneySymbol()) || '₽') + '</strong></span>' +
                '<span class="fw-bold" style="color: ' + sumColor + ';">Сумма: ' + sum + ' ' + ((window.nikaMoneySymbol && window.nikaMoneySymbol()) || '₽') + '</span>' + costSpan +
                '<span><i class="fas fa-calendar me-1"></i>' + escapeHtmlForItems(createdAtStr) + '</span></div></div>' +
                (id != null ? '<button class="btn btn-sm btn-danger ' + (type === 'service' ? 'delete-service-btn' : 'delete-part-btn') + ' ms-2" data-' + (type === 'service' ? 'service-id' : 'part-id') + '="' + id + '" title="Удалить" style="border-radius: 6px; padding: 0.2rem 0.4rem; border: none; background: rgba(239, 68, 68, 0.1); color: #dc2626;"><i class="fas fa-trash" style="font-size: 0.7rem;"></i></button>' : '');
            list.appendChild(item);
        }

        function escapeHtmlForItems(text) {
            const div = document.createElement('div');
            div.textContent = text == null ? '' : String(text);
            return div.innerHTML;
        }

        const LS_KEYS = {
            recent: 'orderAddItems:recent:v1',
            freq: 'orderAddItems:freq:v1',
            lastCategory: 'orderAddItems:lastCategory:v1',
            searchHistory: 'orderAddItems:searchHistory:v1'
        };

        function readSearchHistory() {
            return safeJsonParse(localStorage.getItem(LS_KEYS.searchHistory), []) || [];
        }

        function writeSearchHistory(items) {
            try {
                localStorage.setItem(LS_KEYS.searchHistory, JSON.stringify(items || []));
            } catch (e) {}
        }

        function bumpSearchHistory(query) {
            const q = String(query || '').trim();
            if (!q) return;
            // Не сохраняем слишком короткие/промежуточные запросы
            if (q.length < 3) return;
            if (typeof lastSavedSearchQuery !== 'undefined' && lastSavedSearchQuery && lastSavedSearchQuery.toLowerCase() === q.toLowerCase()) return;
            let items = readSearchHistory().filter(x => String(x || '').trim());
            items = items.filter(x => x.toLowerCase() !== q.toLowerCase());
            items.push(q);
            items = items.slice(-5);
            writeSearchHistory(items);
            if (typeof lastSavedSearchQuery !== 'undefined') lastSavedSearchQuery = q;
            renderSearchHistoryChips();
        }

        function renderSearchHistoryChips() {
            const el = document.getElementById('itemsSearchHistoryChips');
            if (!el) return;
            const items = readSearchHistory();
            el.innerHTML = '';
            if (!items.length) {
                el.style.display = 'none';
                return;
            }
            el.style.display = 'flex';
            items.slice().reverse().forEach(q => {
                const b = document.createElement('button');
                b.type = 'button';
                b.className = 'btn btn-sm btn-outline-secondary';
                b.style.cssText = 'border-radius:999px; padding:0.15rem 0.5rem; font-size:0.72rem; line-height:1.2; max-width: 100%; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;';
                b.textContent = q;
                b.title = q;
                b.addEventListener('click', (ev) => {
                    ev.preventDefault();
                    ev.stopPropagation();
                    const input = document.getElementById('itemsSearchInput');
                    if (!input) return;
                    input.value = q;
                    input.focus();
                    input.dispatchEvent(new Event('input', { bubbles: true }));
                });
                el.appendChild(b);
            });
        }

        // ===== Автодополнение поиска (dropdown) =====
        let itemsAutocompleteResults = [];
        let itemsAutocompleteIndex = -1;
        let lastSavedSearchQuery = null;

        function hideItemsAutocomplete() {
            const el = document.getElementById('itemsSearchAutocomplete');
            if (!el) return;
            el.style.display = 'none';
            el.innerHTML = '';
            itemsAutocompleteResults = [];
            itemsAutocompleteIndex = -1;
        }

        function renderItemsAutocomplete(results) {
            const el = document.getElementById('itemsSearchAutocomplete');
            if (!el) return;
            el.innerHTML = '';

            const list = (results || []).slice(0, 8);
            itemsAutocompleteResults = list;
            itemsAutocompleteIndex = -1;

            if (!list.length) {
                el.style.display = 'none';
                    return;
                }
            el.style.display = 'block';

            list.forEach((it, idx) => {
                const btn = document.createElement('button');
                btn.type = 'button';
                btn.className = 'list-group-item list-group-item-action';
                btn.dataset.idx = String(idx);
                btn.style.cssText = 'display:flex; align-items:center; justify-content:space-between; gap:0.75rem; padding:0.5rem 0.75rem; border: 1px solid rgba(229,231,235,0.6); border-top: none;';
                if (idx === 0) btn.style.borderTop = '1px solid rgba(229,231,235,0.6)';

                const left = document.createElement('div');
                left.style.cssText = 'min-width:0;';
                const name = document.createElement('div');
                name.style.cssText = 'font-weight:600; font-size:0.8rem; color:#111827; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;';
                name.textContent = it.name || '—';
                const meta = document.createElement('div');
                meta.style.cssText = 'font-size:0.7rem; color:#6b7280; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;';
                const typeLabel = it.type === 'service' ? 'Услуга' : 'Товар';
                meta.textContent = typeLabel;
                left.appendChild(name);
                left.appendChild(meta);

                const right = document.createElement('div');
                right.style.cssText = 'flex-shrink:0; display:flex; align-items:center; gap:0.4rem;';
                const price = document.createElement('span');
                price.className = 'text-muted';
                price.style.cssText = 'font-size:0.75rem;';
                price.textContent = `${Number(it.price || 0).toFixed(2)} ${((window.nikaMoneySymbol && window.nikaMoneySymbol()) || '₽')}`;
                right.appendChild(price);

                btn.appendChild(left);
                btn.appendChild(right);

                btn.addEventListener('mouseenter', () => {
                    itemsAutocompleteIndex = idx;
                    highlightItemsAutocomplete();
                });
                btn.addEventListener('click', (ev) => {
                    ev.preventDefault();
                    ev.stopPropagation();
                    pickItemsAutocomplete(idx);
                });

                el.appendChild(btn);
            });
        }

        function highlightItemsAutocomplete() {
            const el = document.getElementById('itemsSearchAutocomplete');
            if (!el) return;
            const buttons = Array.from(el.querySelectorAll('button[data-idx]'));
            buttons.forEach(b => {
                const idx = parseInt(b.dataset.idx || '-1', 10);
                b.classList.toggle('active', idx === itemsAutocompleteIndex);
            });
        }

        function pickItemsAutocomplete(idx) {
            const it = itemsAutocompleteResults[idx];
            if (!it) return;
            // Выбираем позицию и открываем правую панель как при клике по элементу списка
            const type = it.type;
            selectedItem = {
                id: it.id,
                type: type,
                name: it.name,
                price: it.price || 0,
                stock: it.stock_quantity ?? it.stock ?? it.qty ?? it.quantity ?? null,
                cost: it.purchase_price !== undefined ? it.purchase_price : null,
                warranty_days: it.warranty_days !== undefined ? it.warranty_days : null,
                fromCache: false,
                qty: 1
            };
            const selectedItemId = document.getElementById('selectedItemId');
            const selectedItemTypeValue = document.getElementById('selectedItemTypeValue');
            const selectedItemName = document.getElementById('selectedItemName');
            const selectedItemPrice = document.getElementById('selectedItemPrice');
            const saveItemBtn = document.getElementById('saveItemBtn');
            if (selectedItemId) selectedItemId.value = it.id;
            if (selectedItemTypeValue) selectedItemTypeValue.value = type;
            if (selectedItemName) selectedItemName.value = it.name;
            if (selectedItemPrice) selectedItemPrice.value = it.price || 0;
            if (saveItemBtn) saveItemBtn.disabled = false;
            updateSelectedItemPanel();

            hideItemsAutocomplete();
        }

        function safeJsonParse(raw, fallback) {
            try {
                const v = JSON.parse(raw);
                return v === null || v === undefined ? fallback : v;
            } catch {
                return fallback;
            }
        }

        function getItemKey(item) {
            if (!item) return '';
            if (item.id) return `${item.type}:${item.id}`;
            // one-time items: key by name
            return `${item.type}:name:${(item.name || '').toLowerCase()}`;
        }

        function readRecent() {
            return safeJsonParse(localStorage.getItem(LS_KEYS.recent) || '[]', []);
        }

        function readFreq() {
            return safeJsonParse(localStorage.getItem(LS_KEYS.freq) || '{}', {});
        }

        function writeRecent(arr) {
            localStorage.setItem(LS_KEYS.recent, JSON.stringify(arr.slice(0, 50)));
        }

        function writeFreq(obj) {
            localStorage.setItem(LS_KEYS.freq, JSON.stringify(obj));
        }

        function bumpHistory(item) {
            const key = getItemKey(item);
            if (!key) return;
            const now = Date.now();

            const recent = readRecent().filter(x => x && getItemKey(x) !== key);
            recent.unshift({ ...item, ts: now });
            writeRecent(recent.slice(0, 20));

            const freq = readFreq();
            freq[key] = (freq[key] || 0) + 1;
            writeFreq(freq);
        }

        function getRecentByType(type, limit = 10) {
            return readRecent().filter(x => x && x.type === type).slice(0, limit);
        }

        function getFrequentByType(type, limit = 10) {
            const freq = readFreq();
            const recent = readRecent();
            const items = [];
            // rebuild distinct items from recent first to keep name/price data
            const seen = new Set();
            for (const it of recent) {
                if (!it || it.type !== type) continue;
                const k = getItemKey(it);
                if (!k || seen.has(k)) continue;
                seen.add(k);
                items.push({ ...it, count: freq[k] || 0 });
            }
            // also include keys that are not in recent (rare) - skip for simplicity
            items.sort((a, b) => (b.count - a.count) || ((b.ts || 0) - (a.ts || 0)));
            return items.slice(0, limit);
        }

        function renderHistoryList(containerId, items) {
            const el = document.getElementById(containerId);
            if (!el) return;
            el.innerHTML = '';
            // Вертикальный столбик тегов (без горизонтальной прокрутки)
            el.style.display = 'block';
            el.style.overflowY = 'auto';
            el.style.maxHeight = '200px';
            if (!items || !items.length) {
                const empty = document.createElement('div');
                empty.className = 'text-muted small';
                empty.style.padding = '0.25rem 0';
                empty.textContent = '—';
                el.appendChild(empty);
                return;
            }
            items.forEach(it => {
                const tag = document.createElement('button');
                tag.type = 'button';
                tag.className = 'btn btn-sm btn-outline-secondary d-block w-100 mb-1 text-start';
                tag.style.cssText = 'font-size: 0.72rem; padding: 0.22rem 0.45rem; border-radius: 999px; border: 1px solid rgba(229, 231, 235, 0.55); background: rgba(249, 250, 251, 0.55); transition: all 0.2s; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;';
                tag.textContent = it.name || '—';
                // Цена показывается при наведении
                tag.title = `${(Number(it.price || 0)).toFixed(2)} ${((window.nikaMoneySymbol && window.nikaMoneySymbol()) || '₽')}`;
                
                // Hover эффект
                tag.addEventListener('mouseenter', function() {
                    this.style.backgroundColor = 'rgba(59, 130, 246, 0.1)';
                    this.style.borderColor = '#3b82f6';
                    this.style.transform = 'translateX(1px)';
                });
                tag.addEventListener('mouseleave', function() {
                    this.style.backgroundColor = 'rgba(249, 250, 251, 0.6)';
                    this.style.borderColor = 'rgba(229, 231, 235, 0.5)';
                    this.style.transform = 'translateX(0)';
                });
                
                // Клик - добавляем или выбираем позицию
                tag.addEventListener('click', async (ev) => {
                    ev.preventDefault();
                    ev.stopPropagation();
                    // Если это разовая позиция (нет id) — откроем разовую форму и заполним
                    if (!it.id) {
                        const openBtn = document.getElementById(it.type === 'service' ? 'openOneTimeServiceBtn' : 'openOneTimePartBtn');
                        if (openBtn) openBtn.click();
                        const n = document.getElementById('oneTimeNameInput');
                        const p = document.getElementById('oneTimePriceInput');
                        const q = document.getElementById('oneTimeQtyInput');
                        const costInp = document.getElementById('oneTimeCostInput');
                        if (n) n.value = it.name || '';
                        if (p) p.value = String(Number(it.price || 0));
                        if (q) q.value = String(it.quantity || 1);
                        if (costInp && (it.cost != null || it.purchase_price != null)) costInp.value = String(it.cost ?? it.purchase_price ?? '');
                        return;
                    }
                    // Если есть id - выбираем позицию (из Recent/Frequent). Подгружаем актуальные цена и остаток из справочников
                    let stock = it.stock_quantity ?? it.stock ?? it.quantity ?? null;
                    let price = it.price || 0;
                    let cost = it.cost ?? it.purchase_price ?? null;
                    if (it.type === 'part' && it.id) {
                        try {
                            const r = await fetch(`/warehouse/api/part/${it.id}/stock`);
                            const d = await r.json();
                            if (d.success) {
                                if (d.stock_quantity !== undefined) stock = d.stock_quantity;
                                if (d.price !== undefined && d.price !== null) price = Number(d.price);
                                if (d.purchase_price != null) cost = Number(d.purchase_price);
                            }
                        } catch (e) { /* оставляем из кеша */ }
                    } else if (it.type === 'service' && it.id) {
                        try {
                            const svc = (typeof allServicesData !== 'undefined' ? allServicesData : []).find(s => s.id === it.id);
                            if (svc && svc.price != null) price = Number(svc.price);
                            else {
                                const r = await fetch(`/api/services/${it.id}`);
                                const d = await r.json();
                                if (d.success && d.price != null) price = Number(d.price);
                            }
                        } catch (e) { /* оставляем из кеша */ }
                    }
                    selectedItem = {
                        id: it.id,
                        type: it.type,
                        name: it.name,
                        price: price,
                        cost: cost,
                        stock,
                        fromCache: true,
                        qty: 1
                    };
                    const selectedItemId = document.getElementById('selectedItemId');
                    const selectedItemTypeValue = document.getElementById('selectedItemTypeValue');
                    const selectedItemName = document.getElementById('selectedItemName');
                    const selectedItemPrice = document.getElementById('selectedItemPrice');
                    const saveItemBtn = document.getElementById('saveItemBtn');
                    if (selectedItemId) selectedItemId.value = it.id;
                    if (selectedItemTypeValue) selectedItemTypeValue.value = it.type;
                    if (selectedItemName) selectedItemName.value = it.name;
                    if (selectedItemPrice) selectedItemPrice.value = price;
                    if (saveItemBtn) saveItemBtn.disabled = false;
                    updateSelectedItemPanel();
                });

                el.appendChild(tag);
            });
        }

        function setItemsView(view) {
            currentItemsView = view;
            const home = document.getElementById('itemsHomeView');
            const searchView = document.getElementById('itemsSearchResultsView');
            const browseServices = document.getElementById('itemsBrowseServicesView');
            const browseParts = document.getElementById('itemsBrowsePartsView');
            const noResults = document.getElementById('noResultsMessage');

            if (home) home.style.display = (view === 'home') ? 'block' : 'none';
            if (searchView) searchView.style.display = (view === 'search') ? 'block' : 'none';
            if (browseServices) browseServices.style.display = (view === 'services') ? 'block' : 'none';
            if (browseParts) browseParts.style.display = (view === 'parts') ? 'block' : 'none';

            // noResults показываем только в режиме поиска, когда нет результатов
            if (noResults && view !== 'search') {
                noResults.style.display = 'none';
            }
        }

        function resetItemsSelection() {
            selectedItem = null;
            const selectedItemId = document.getElementById('selectedItemId');
            const selectedItemTypeValue = document.getElementById('selectedItemTypeValue');
            const selectedItemName = document.getElementById('selectedItemName');
            const selectedItemPrice = document.getElementById('selectedItemPrice');
            const saveBtn = document.getElementById('saveItemBtn');
            if (selectedItemId) selectedItemId.value = '';
            if (selectedItemTypeValue) selectedItemTypeValue.value = '';
            if (selectedItemName) selectedItemName.value = '';
            if (selectedItemPrice) selectedItemPrice.value = '';
            if (saveBtn) saveBtn.disabled = true;

            const panel = document.getElementById('selectedItemPanel');
            if (panel) panel.style.display = 'none';
            
            // Возвращаем модалку к исходному размеру
            const modalDialog = document.getElementById('addItemsModalDialog');
            if (modalDialog) {
                modalDialog.classList.remove('modal-xl');
                modalDialog.classList.add('modal-lg');
            }
        }

        function updateSelectedItemPanel() {
            const panel = document.getElementById('selectedItemPanel');
            const titleEl = document.getElementById('selectedItemTitle');
            const metaEl = document.getElementById('selectedItemMeta');
            const qtyInput = document.getElementById('selectedItemQtyInput');
            const priceInput = document.getElementById('selectedItemPriceInput');
            const costInput = document.getElementById('selectedItemCostInput');
            const warrantyInput = document.getElementById('selectedItemWarrantyInput');
            const discountInput = document.getElementById('selectedItemDiscountInput');
            const executorSelect = document.getElementById('selectedItemExecutorSelect');
            const btnPct = document.getElementById('discountTypePercentBtn');
            const btnRub = document.getElementById('discountTypeRubBtn');
            const saveBtn = document.getElementById('saveItemBtn');
            if (!panel || !titleEl || !metaEl || !qtyInput || !priceInput || !saveBtn) return;

            // Управление расширением модалки
            const modalDialog = document.getElementById('addItemsModalDialog');
            
            if (!selectedItem) {
                panel.style.display = 'none';
                // Возвращаем модалку к исходному размеру
                if (modalDialog) {
                    modalDialog.classList.remove('modal-xl');
                    modalDialog.classList.add('modal-lg');
                }
                return;
            }

            panel.style.display = 'block';
            // Расширяем модалку при выборе позиции
            if (modalDialog) {
                modalDialog.classList.remove('modal-lg');
                modalDialog.classList.add('modal-xl');
                // Плавная анимация
                modalDialog.style.transition = 'all 0.3s ease-in-out';
            }
            titleEl.textContent = selectedItem.name || '—';

            const stock = selectedItem.stock;
            const stockText = (selectedItem.type === 'part' && stock !== null && stock !== undefined)
                ? `Остаток: ${stock} шт.`
                : '';
            const priceText = `Цена: ${(Number(selectedItem.price || 0)).toFixed(2)} ${((window.nikaMoneySymbol && window.nikaMoneySymbol()) || '₽')}`;
            metaEl.textContent = [stockText, priceText].filter(Boolean).join(' • ');

            qtyInput.value = String(selectedItem.qty || 1);
            priceInput.value = selectedItem.price !== null && selectedItem.price !== undefined
                ? Number(selectedItem.price || 0).toFixed(2)
                : '';
            saveBtn.disabled = false;

            if (discountInput) discountInput.value = '';
            if (executorSelect) executorSelect.value = '';

            if (costInput) {
                costInput.value = (selectedItem.cost !== null && selectedItem.cost !== undefined && selectedItem.cost !== '')
                    ? String(selectedItem.cost)
                    : '';
            }

            if (warrantyInput) {
                let w = selectedItem.warranty_days;
                if (w === null || w === undefined || w === '') {
                    w = (window.NIKA_ORDER_PAGE && window.NIKA_ORDER_PAGE.defaultWarrantyDays != null) ? window.NIKA_ORDER_PAGE.defaultWarrantyDays : 30;
                }
                warrantyInput.value = String(w);
            }

            function renderDiscountButtons() {
                if (!btnPct || !btnRub) return;
                btnPct.classList.toggle('active', discountType === 'percent');
                btnRub.classList.toggle('active', discountType === 'amount');
            }
            if (btnPct && !btnPct.dataset.bound) {
                btnPct.dataset.bound = '1';
                btnPct.addEventListener('click', () => {
                    discountType = 'percent';
                    renderDiscountButtons();
                });
            }
            if (btnRub && !btnRub.dataset.bound) {
                btnRub.dataset.bound = '1';
                btnRub.addEventListener('click', () => {
                    discountType = 'amount';
                    renderDiscountButtons();
                });
            }
            renderDiscountButtons();
        }

        
        // Функция отображения результатов поиска
        function displaySearchResults(results) {
            const servicesList = document.getElementById('servicesList');
            const partsList = document.getElementById('partsList');
            const noResultsMessage = document.getElementById('noResultsMessage');
            const servicesCategory = document.getElementById('servicesCategory');
            const partsCategory = document.getElementById('partsCategory');
            
            if (!servicesList || !partsList) return;
            
            // Очищаем списки
            servicesList.innerHTML = '';
            partsList.innerHTML = '';
            
            // Разделяем результаты на услуги и товары
            const services = results.filter(item => item.type === 'service');
            const parts = results.filter(item => item.type === 'part');
            
            // Отображаем услуги
            if (services.length > 0) {
                servicesCategory.style.display = 'block';
                            services.forEach(service => {
                    const item = createListItem(service, 'service');
                    servicesList.appendChild(item);
                });
            } else {
                servicesCategory.style.display = 'none';
            }
            
            // Отображаем товары
            if (parts.length > 0) {
                partsCategory.style.display = 'block';
                parts.forEach(part => {
                    const item = createListItem(part, 'part');
                    partsList.appendChild(item);
                });
            } else {
                partsCategory.style.display = 'none';
            }
            
            // Показываем сообщение, если нет результатов
            if (services.length === 0 && parts.length === 0) {
                noResultsMessage.style.display = 'block';
            } else {
                noResultsMessage.style.display = 'none';
            }
        }
        
        // Функция создания элемента списка
        function createListItem(item, type, options = {}) {
            const listItem = document.createElement('div');
            listItem.className = 'list-group-item list-group-item-action items-selectable';
            listItem.tabIndex = 0;
            listItem.style.cssText = 'cursor: pointer; padding: 0.75rem 1rem; border: 1px solid rgba(229, 231, 235, 0.3); margin-bottom: 0.25rem; border-radius: 6px; transition: all 0.2s;';
            
            listItem.addEventListener('mouseenter', function() {
                this.style.backgroundColor = 'rgba(59, 130, 246, 0.1)';
                this.style.borderColor = '#3b82f6';
            });
            
            listItem.addEventListener('mouseleave', function() {
                if (selectedItem && selectedItem.id === item.id && selectedItem.type === type) {
                    this.style.backgroundColor = 'rgba(59, 130, 246, 0.15)';
                    this.style.borderColor = '#3b82f6';
                } else {
                    this.style.backgroundColor = '';
                    this.style.borderColor = 'rgba(229, 231, 235, 0.3)';
                }
            });
            
            // Обработчик клика
            listItem.addEventListener('click', function() {
                // Убираем выделение с предыдущего элемента
                document.querySelectorAll('.list-group-item').forEach(el => {
                    if (el !== this) {
                        el.style.backgroundColor = '';
                        el.style.borderColor = 'rgba(229, 231, 235, 0.3)';
                    }
                });
                
                // Выделяем текущий элемент
                this.style.backgroundColor = 'rgba(59, 130, 246, 0.15)';
                this.style.borderColor = '#3b82f6';
                
                // Сохраняем выбранный элемент (из основного списка — stock актуальный)
                selectedItem = {
                    id: item.id,
                    type: type,
                    name: item.name,
                    price: item.price || 0,
                    stock: item.stock_quantity !== undefined ? item.stock_quantity : (item.quantity !== undefined ? item.quantity : (item.stock !== undefined && item.stock !== null ? item.stock : null)),
                    cost: item.purchase_price !== undefined ? item.purchase_price : null,
                    warranty_days: item.warranty_days !== undefined ? item.warranty_days : null,
                    fromCache: false,
                    qty: 1
                };
                
                // Заполняем скрытые поля
                                    const selectedItemId = document.getElementById('selectedItemId');
                                    const selectedItemTypeValue = document.getElementById('selectedItemTypeValue');
                const selectedItemName = document.getElementById('selectedItemName');
                const selectedItemPrice = document.getElementById('selectedItemPrice');
                                    const saveItemBtn = document.getElementById('saveItemBtn');
                                    
                if (selectedItemId) selectedItemId.value = item.id;
                if (selectedItemTypeValue) selectedItemTypeValue.value = type;
                if (selectedItemName) selectedItemName.value = item.name;
                if (selectedItemPrice) selectedItemPrice.value = item.price || 0;
                if (saveItemBtn) saveItemBtn.disabled = false;

                updateSelectedItemPanel();
            });
            
            // Содержимое элемента
            const row = document.createElement('div');
            row.className = 'd-flex justify-content-between align-items-start gap-2';

            const left = document.createElement('div');
            left.className = 'flex-grow-1';

            const name = document.createElement('div');
            name.className = 'fw-bold';
            name.textContent = item.name;
            name.style.cssText = 'color: #111827; margin-bottom: 0.25rem;';

            if (options.showTypeBadge) {
                const badge = document.createElement('span');
                badge.className = `badge ${type === 'service' ? 'bg-primary' : 'bg-secondary'} me-2`;
                badge.style.fontSize = '0.7rem';
                badge.textContent = type === 'service' ? 'Услуга' : 'Товар';
                const wrap = document.createElement('div');
                wrap.appendChild(badge);
                wrap.appendChild(name);
                left.appendChild(wrap);
                                } else {
                left.appendChild(name);
            }

            const price = document.createElement('div');
            price.className = 'text-success';
            price.textContent = `${(item.price || 0).toFixed(2)} ${((window.nikaMoneySymbol && window.nikaMoneySymbol()) || '₽')}`;
            price.style.cssText = 'font-size: 0.875rem;';
            left.appendChild(price);

            // Для товаров добавляем информацию об остатке
            const stockQty = item.stock_quantity !== undefined ? item.stock_quantity
                : (item.quantity !== undefined ? item.quantity
                    : (item.stock !== undefined && item.stock !== null ? item.stock : null));
            if (type === 'part' && stockQty !== null && stockQty !== undefined) {
                const stockLine = document.createElement('div');
                stockLine.style.cssText = 'margin-top: 0.25rem;';

                const qtyNum = Number(stockQty);
                const badge = document.createElement('span');
                badge.className = 'badge';
                badge.style.cssText = 'font-size:0.68rem; padding:0.18rem 0.4rem; border-radius:999px; border: 1px solid rgba(229,231,235,0.8);';
                if (qtyNum <= 0) {
                    badge.style.background = 'rgba(239, 68, 68, 0.12)';
                    badge.style.color = '#dc2626';
                    badge.textContent = 'Нет';
                } else if (qtyNum <= 10) {
                    badge.style.background = 'rgba(245, 158, 11, 0.14)';
                    badge.style.color = '#b45309';
                    badge.textContent = `${qtyNum} шт.`;
                        } else {
                    badge.style.background = 'rgba(34, 197, 94, 0.14)';
                    badge.style.color = '#15803d';
                    badge.textContent = `${qtyNum} шт.`;
                }
                badge.title = qtyNum <= 0 ? 'Нет в наличии' : `Остаток: ${qtyNum} шт.`;

                const label = document.createElement('span');
                label.className = 'text-muted ms-2';
                label.style.cssText = 'font-size:0.72rem;';
                label.textContent = 'Остаток';

                stockLine.appendChild(badge);
                stockLine.appendChild(label);
                left.appendChild(stockLine);
            }

            const right = document.createElement('div');
            right.className = 'd-flex align-items-center';

            // Быстрое добавление "+"
            const plusBtn = document.createElement('button');
            plusBtn.type = 'button';
            plusBtn.className = 'btn btn-sm btn-outline-primary';
            plusBtn.style.cssText = 'border-radius: 8px; padding: 0.25rem 0.5rem;';
            plusBtn.innerHTML = '<i class="fas fa-plus"></i>';
            plusBtn.addEventListener('click', async (ev) => {
                ev.preventDefault();
                ev.stopPropagation();
                await quickAddItem({
                    id: item.id,
                    type,
                    name: item.name,
                    price: item.price || 0,
                    stock: stockQty
                });
            });
            right.appendChild(plusBtn);

            row.appendChild(left);
            row.appendChild(right);
            listItem.appendChild(row);
            
            return listItem;
        }

        async function postAddItem({ type, id, name, quantity, price, cost_price, purchase_price }) {
            const orderId = numericOrderId();
            if (!orderId) throw new Error('Не удалось определить заявку');
            const endpoint = type === 'service' ? `/api/orders/${orderId}/services` : `/api/orders/${orderId}/parts`;
            const payload = type === 'service'
                ? { service_id: id || null, name: id ? null : name, quantity, price, cost_price: cost_price ?? null }
                : { part_id: id || null, name: id ? null : name, quantity, price, purchase_price: purchase_price ?? null };

            const resp = await fetch(endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await resp.json();
            if (!data.success) throw new Error(data.error || 'Ошибка добавления');
            return data;
        }

        async function quickAddItem(item) {
            try {
                // строгий контроль остатков: запрет, если нет
                if (item.type === 'part' && item.stock !== null && item.stock !== undefined) {
                    const stock = Number(item.stock);
                    if (Number.isFinite(stock) && stock <= 0) {
                        showToast('Нет остатка. Добавьте через приход склада.', 'error', 'Склад');
                return;
                    }
                }
                const orderId = numericOrderId();
                if (!orderId) {
                    showToast('Не удалось определить заявку', 'error');
                    return;
                }
                const endpoint = item.type === 'service'
                    ? `/api/orders/${orderId}/services`
                    : `/api/orders/${orderId}/parts`;
                const payload = item.type === 'service'
                    ? { service_id: item.id, quantity: 1, price: item.price, base_price: item.price }
                    : { part_id: item.id, quantity: 1, price: item.price, base_price: item.price };
                const resp = await fetch(endpoint, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const data = await resp.json();
                if (!data.success) {
                    showToast(data.error || 'Не удалось добавить', 'error', 'Ошибка');
                    return;
                }
                // Обновляем суммы заявки, если они есть в ответе
                if (data.order_total !== undefined) {
                    updateOrderTotals(
                        data.order_total || 0,
                        data.order_paid || 0,
                        data.order_debt || 0,
                        data.prepayment || 0,
                        data.overpayment || 0
                    );
                }
                // Сразу показываем добавленную позицию в списке на странице
                if (item.type === 'service' && data.services && data.services.length) {
                    const last = data.services[data.services.length - 1];
                    appendOrderItemToPage('service', { id: last.id, name: last.service_name || item.name, quantity: last.quantity || 1, price: last.price != null ? last.price : item.price, cost_price: last.cost_price ?? item.cost });
                } else if (item.type === 'part' && data.order_part_id != null) {
                    appendOrderItemToPage('part', { id: data.order_part_id, name: item.name, quantity: 1, price: item.price, purchase_price: item.purchase_price ?? item.cost });
                }
                bumpHistory({ type: item.type, id: item.id, name: item.name, price: item.price, stock_quantity: item.stock });
                showToast('Добавлено', 'success');
                markItemsAdded(item.name);
                afterSuccessfulItemsAdd();
                return data;
            } catch (e) {
                console.error(e);
                showToast(e.message || 'Не удалось добавить', 'error', 'Ошибка');
            }
        }
        
        // Инициализация поиска
        function initItemsSearch() {
            const searchInput = document.getElementById('itemsSearchInput');
            
            if (!searchInput) {
                console.error('Поле поиска не найдено');
                return;
            }
            
            if (itemsSearchInitialized) return;
            itemsSearchInitialized = true;

            // История поиска
            renderSearchHistoryChips();
            // Автодополнение: скрываем при потере фокуса (с задержкой, чтобы успеть кликнуть)
            searchInput.addEventListener('blur', () => setTimeout(hideItemsAutocomplete, 150));
            searchInput.addEventListener('focus', () => {
                if (itemsAutocompleteResults && itemsAutocompleteResults.length) {
                    const el = document.getElementById('itemsSearchAutocomplete');
                    if (el) el.style.display = 'block';
                }
            });
            
            // Обработчик ввода
            searchInput.addEventListener('input', function() {
                const query = this.value.trim();
                
                clearTimeout(itemsSearchTimeout);
                
                // Если запрос пустой, очищаем результаты
                if (query.length === 0) {
                    displaySearchResults([]);
                    // возвращаемся в последний browse view
                    setItemsView(lastBrowseView || 'home');
                    const noResultsMessage = document.getElementById('noResultsMessage');
                    if (noResultsMessage) noResultsMessage.style.display = 'none';
                    resetItemsSelection();
                    hideItemsAutocomplete();
                    
                    // Сбрасываем выделение элементов
                    document.querySelectorAll('.list-group-item').forEach(el => {
                        el.style.backgroundColor = '';
                        el.style.borderColor = 'rgba(229, 231, 235, 0.3)';
                    });
                    return;
                }
                
                // Задержка перед поиском (автопоиск): /api/search/items — без права view_shop, совместимо с PostgreSQL
                itemsSearchTimeout = setTimeout(async () => {
                    try {
                        const response = await fetch(`/api/search/items?q=${encodeURIComponent(query)}`);
                        
                        if (!response.ok) {
                            throw new Error(`HTTP error! status: ${response.status}`);
                        }
                        
                        const data = await response.json();
                        const items = (data.success && data.items) ? data.items : [];
                        
                        if (items.length > 0) {
                            bumpSearchHistory(query);
                            lastBrowseView = currentItemsView === 'search' ? (lastBrowseView || 'home') : currentItemsView;
                            setItemsView('search');
                            displaySearchResults(items);
                            renderItemsAutocomplete(items);
                        } else {
                            lastBrowseView = currentItemsView === 'search' ? (lastBrowseView || 'home') : currentItemsView;
                            setItemsView('search');
                            displaySearchResults([]);
                            hideItemsAutocomplete();
                        }
                    } catch (error) {
                        console.error('Ошибка поиска:', error);
                        lastBrowseView = currentItemsView === 'search' ? (lastBrowseView || 'home') : currentItemsView;
                        setItemsView('search');
                        displaySearchResults([]);
                        hideItemsAutocomplete();
                    }
                }, 300); // Задержка 300мс для автопоиска
            });
        }

        function normalizeServiceList(raw) {
            if (!Array.isArray(raw)) return [];
            // Не переупорядочиваем без необходимости: справочник уже может быть отсортирован.
            // Если есть sort_order — используем его.
            const hasSort = raw.some(s => s && (s.sort_order !== undefined && s.sort_order !== null));
            const list = raw
                .map(s => ({
                    id: s.id,
                    name: s.name,
                    price: Number(s.price || 0),
                    sort_order: s.sort_order,
                    usage_count: Number(s.usage_count || 0)
                }))
                .filter(s => s.id && s.name);
            list.sort((a, b) => {
                const usageDiff = (Number(b.usage_count || 0) - Number(a.usage_count || 0));
                if (usageDiff) return usageDiff;
                if (hasSort) {
                    const so = (Number(a.sort_order || 0) - Number(b.sort_order || 0));
                    if (so) return so;
                }
                return a.name.localeCompare(b.name, 'ru');
            });
            return list;
        }

        function renderServicesBrowse() {
            const container = document.getElementById('servicesBrowseList');
            if (!container) return;
            container.innerHTML = '';
            const services = normalizeServiceList(typeof allServicesData !== 'undefined' ? allServicesData : []);
            services.forEach(svc => {
                const el = createListItem({ id: svc.id, name: svc.name, price: svc.price }, 'service');
                container.appendChild(el);
            });

            renderHistoryList('servicesRecentList', getRecentByType('service'));
            renderHistoryList('servicesFrequentList', getFrequentByType('service'));
        }

        function flattenCategoriesTree(nodes, depth = 0, out = []) {
            if (!Array.isArray(nodes)) return out;
            nodes.forEach(n => {
                if (!n) return;
                out.push({ name: n.name, depth });
                if (Array.isArray(n.children) && n.children.length) {
                    flattenCategoriesTree(n.children, depth + 1, out);
                }
            });
            return out;
        }

        async function ensurePartsCategoriesLoaded() {
            const select = document.getElementById('partsCategoryBrowseSelect');
            if (!select) return;
            // если уже наполнено — не трогаем
            if (select.dataset.loaded === '1') return;

            try {
                const resp = await fetch('/warehouse/categories');
                const data = await resp.json();
                const flat = flattenCategoriesTree(data);
                flat.forEach(cat => {
                    const opt = document.createElement('option');
                    opt.value = cat.name;
                    opt.textContent = `${'— '.repeat(Math.min(cat.depth, 6))}${cat.name}`;
                    select.appendChild(opt);
                });
                select.dataset.loaded = '1';
            } catch (e) {
                console.error('Не удалось загрузить категории:', e);
            }
        }

        async function loadPartsForBrowse(categoryName = '') {
            const list = document.getElementById('partsBrowseList');
            if (!list) return;
            list.innerHTML = '';
            try {
                const base = categoryName ? `/warehouse/api/parts?category=${encodeURIComponent(categoryName)}` : '/warehouse/api/parts';
                const url = base + (base.includes('?') ? '&' : '?') + '_=' + Date.now();
                const resp = await fetch(url);
                const data = await resp.json();
                if (!data.success) return;
                (data.items || []).forEach(p => {
                    const price = Number(p.retail_price ?? p.price ?? 0);
                    const stock = p.stock_quantity ?? p.stock ?? p.quantity ?? null;
                    const item = {
                        id: p.id,
                        name: p.name,
                        price,
                        stock_quantity: stock,
                        purchase_price: p.purchase_price ?? null,
                        warranty_days: p.warranty_days ?? null
                    };
                    const el = createListItem(item, 'part');
                    list.appendChild(el);
                });

                renderHistoryList('partsRecentList', getRecentByType('part'));
                renderHistoryList('partsFrequentList', getFrequentByType('part'));
            } catch (e) {
                console.error('Не удалось загрузить товары:', e);
            }
        }

        function initItemsBrowseNav() {
            if (itemsBrowseInitialized) return;
            itemsBrowseInitialized = true;

            const btnServices = document.getElementById('openServicesListBtn');
            const btnParts = document.getElementById('openPartsListBtn');
            const backServices = document.getElementById('itemsBrowseBackBtnServices');
            const backParts = document.getElementById('itemsBrowseBackBtnParts');
            const partsSelect = document.getElementById('partsCategoryBrowseSelect');

            if (btnServices) {
                btnServices.addEventListener('click', async () => {
                    lastBrowseView = 'home';
                    setItemsView('services');
                    await ensureServicesLoaded();
                    renderServicesBrowse();
                });
            }

            if (btnParts) {
                btnParts.addEventListener('click', async () => {
                    lastBrowseView = 'home';
                    setItemsView('parts');
                    await ensurePartsCategoriesLoaded();
                    const savedCat = localStorage.getItem(LS_KEYS.lastCategory) || '';
                    const partsSelect = document.getElementById('partsCategoryBrowseSelect');
                    if (partsSelect && savedCat) partsSelect.value = savedCat;
                    await loadPartsForBrowse(savedCat || '');
                });
            }

            if (backServices) {
                backServices.addEventListener('click', () => {
                    setItemsView('home');
                });
            }

            if (backParts) {
                backParts.addEventListener('click', () => {
                    setItemsView('home');
                });
            }

            if (partsSelect) {
                partsSelect.addEventListener('change', async () => {
                    localStorage.setItem(LS_KEYS.lastCategory, partsSelect.value || '');
                    await loadPartsForBrowse(partsSelect.value || '');
                });
            }
        }

        function initItemsKeyboard() {
            if (itemsKeyboardInitialized) return;
            itemsKeyboardInitialized = true;
            const modal = document.getElementById('addItemsModal');
            if (!modal) return;
            modal.addEventListener('keydown', (e) => {
                // Ctrl+F или / - фокус в поле поиска
                if ((e.ctrlKey && e.key === 'f') || (e.key === '/' && !e.ctrlKey && !e.altKey && !e.shiftKey)) {
                    const searchInput = document.getElementById('itemsSearchInput');
                    if (searchInput && document.activeElement !== searchInput) {
                        e.preventDefault();
                        searchInput.focus();
                        searchInput.select();
                        return;
                    }
                }
                
                // Tab - переключение между списками (если не в поле ввода)
                if (e.key === 'Tab' && !e.ctrlKey && !e.altKey) {
                    const activeEl = document.activeElement;
                    const isInput = activeEl.tagName === 'INPUT' || activeEl.tagName === 'TEXTAREA' || activeEl.tagName === 'SELECT';
                    if (!isInput) {
                        const servicesBtn = document.getElementById('openServicesListBtn');
                        const partsBtn = document.getElementById('openPartsListBtn');
                        if (servicesBtn && partsBtn) {
                            e.preventDefault();
                            // Простое переключение между кнопками
                            if (document.activeElement === servicesBtn) {
                                partsBtn.focus();
                            } else if (document.activeElement === partsBtn) {
                                servicesBtn.focus();
                        } else {
                                servicesBtn.focus();
                            }
                            return;
                        }
                    }
                }
                
                if (e.key === 'Escape') {
                    const inst = bootstrap.Modal.getInstance(modal);
                    if (inst) inst.hide();
                    return;
                }
                if (e.key === 'Enter') {
                    // Если фокус в поиске и открыт автодоп — выбираем подсказку
                    const searchInput = document.getElementById('itemsSearchInput');
                    const autoEl = document.getElementById('itemsSearchAutocomplete');
                    if (searchInput && document.activeElement === searchInput && autoEl && autoEl.style.display !== 'none') {
                        if (itemsAutocompleteResults && itemsAutocompleteResults.length) {
                            if (itemsAutocompleteIndex < 0) itemsAutocompleteIndex = 0;
                            pickItemsAutocomplete(itemsAutocompleteIndex);
                            e.preventDefault();
                            return;
                        }
                    }
                    // если открыт one-time — добавляем one-time
                    const oneTimeVisible = document.getElementById('oneTimeForm')?.style.display !== 'none';
                    if (oneTimeVisible) {
                        const btn = document.getElementById('addOneTimeBtn');
                        if (btn) btn.click();
                        e.preventDefault();
                        return;
                    }
                    const btn = document.getElementById('saveItemBtn');
                    if (btn && !btn.disabled) {
                        btn.click();
                        e.preventDefault();
                        return;
                    }
                }
                if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
                    // Если фокус в поиске и открыт автодоп — двигаемся по подсказкам
                    const searchInput = document.getElementById('itemsSearchInput');
                    const autoEl = document.getElementById('itemsSearchAutocomplete');
                    if (searchInput && document.activeElement === searchInput && autoEl && autoEl.style.display !== 'none') {
                        const max = (itemsAutocompleteResults || []).length - 1;
                        if (max >= 0) {
                            if (itemsAutocompleteIndex < 0) itemsAutocompleteIndex = 0;
                            itemsAutocompleteIndex = e.key === 'ArrowDown'
                                ? Math.min(max, itemsAutocompleteIndex + 1)
                                : Math.max(0, itemsAutocompleteIndex - 1);
                            highlightItemsAutocomplete();
                            e.preventDefault();
                            return;
                        }
                    }
                    const visibleLists = [
                        'servicesList','partsList','servicesBrowseList','partsBrowseList'
                    ].map(id => document.getElementById(id)).filter(Boolean);
                    let activeList = visibleLists.find(l => l.offsetParent !== null);
                    if (!activeList) return;
                    const items = Array.from(activeList.querySelectorAll('.items-selectable'));
                    if (!items.length) return;
                    const focused = document.activeElement;
                    let idx = items.indexOf(focused);
                    if (idx < 0) idx = 0;
                    idx = e.key === 'ArrowDown' ? Math.min(items.length - 1, idx + 1) : Math.max(0, idx - 1);
                    items[idx].focus();
                    e.preventDefault();
                }
            });
        }

        // Инициализация при открытии модального окна
        const addItemsModal = document.getElementById('addItemsModal');
        if (addItemsModal) {
            // Страховка: если кнопка "Добавить" находится внутри <form> или есть чужие preventDefault,
            // принудительно открываем модалку через JS (capture-phase).
            whenDOMReady(function() {
                const openBtn = document.getElementById('openAddItemsModalBtn');
                if (!openBtn) return;
                openBtn.addEventListener('click', function(e) {
                    // Не даем форме сабмититься
                    try { e.preventDefault(); } catch (err) {}
                    try { e.stopPropagation(); } catch (err) {}
                    try {
                        bootstrap.Modal.getOrCreateInstance(addItemsModal).show();
                    } catch (err) {
                        console.error('Не удалось открыть модалку addItemsModal:', err);
                    }
                }, true);
            });

            addItemsModal.addEventListener('shown.bs.modal', function() {
                // Инициализируем поиск
                setTimeout(() => {
                    initItemsSearch();
                    initItemsBrowseNav();
                    initItemsKeyboard();
                
                // Очищаем форму
                    const searchInput = document.getElementById('itemsSearchInput');
                const selectedItemId = document.getElementById('selectedItemId');
                const selectedItemTypeValue = document.getElementById('selectedItemTypeValue');
                    const selectedItemName = document.getElementById('selectedItemName');
                    const selectedItemPrice = document.getElementById('selectedItemPrice');
                const saveItemBtn = document.getElementById('saveItemBtn');
                
                    if (searchInput) searchInput.value = '';
                if (selectedItemId) selectedItemId.value = '';
                if (selectedItemTypeValue) selectedItemTypeValue.value = '';
                    if (selectedItemName) selectedItemName.value = '';
                    if (selectedItemPrice) selectedItemPrice.value = '';
                if (saveItemBtn) saveItemBtn.disabled = true;
                itemsModalDirty = false;
                itemsAddedNames = [];
                updateAddedSummaryUI();
                    
                    // Очищаем результаты
                    displaySearchResults([]);
                    resetItemsSelection();
                    
                    // Домашний экран
                    setItemsView('home');
                    lastBrowseView = 'home';

                    renderHistoryList('homeRecentList', readRecent().slice(0, 10));
                    // for home frequent: merge top by count from recent
                    const freq = getFrequentByType('service', 5).concat(getFrequentByType('part', 5));
                    freq.sort((a,b)=> (Number(b.count || 0) - Number(a.count || 0)) );
                    renderHistoryList('homeFrequentList', freq.slice(0, 10));

                    // Показываем сообщение о начале поиска (в режиме search оно управляется displaySearchResults)
                    const noResultsMessage = document.getElementById('noResultsMessage');
                    const servicesCategory = document.getElementById('servicesCategory');
                    const partsCategory = document.getElementById('partsCategory');
                    if (noResultsMessage) noResultsMessage.style.display = 'none';
                    if (servicesCategory) servicesCategory.style.display = 'none';
                    if (partsCategory) partsCategory.style.display = 'none';

                    // Автофокус на поиске при открытии модалки
                    if (searchInput) {
                        searchInput.focus();
                        try { searchInput.select(); } catch (e) {}
                    }
                }, 100);
            });

            // После закрытия модалки — обновляем страницу, если что-то добавляли
            addItemsModal.addEventListener('hidden.bs.modal', function() {
                if (itemsModalDirty) {
                    location.reload();
                }
            });
        }

        // Управление one-time формой
        (function initOneTimeUI(){
            const openSvc = document.getElementById('openOneTimeServiceBtn');
            const openPart = document.getElementById('openOneTimePartBtn');
            const form = document.getElementById('oneTimeForm');
            const title = document.getElementById('oneTimeTitle');
            const name = document.getElementById('oneTimeNameInput');
            const qty = document.getElementById('oneTimeQtyInput');
            const price = document.getElementById('oneTimePriceInput');
            const costInput = document.getElementById('oneTimeCostInput');
            const addBtn = document.getElementById('addOneTimeBtn');
            const cancelBtn = document.getElementById('cancelOneTimeBtn');
            const clearSel = document.getElementById('clearSelectedItemBtn');

            if (clearSel) {
                clearSel.addEventListener('click', () => {
                    resetItemsSelection();
                });
            }

            function open(type){
                oneTimeMode = type;
                if (form) form.style.display = 'block';
                if (title) title.textContent = type === 'service' ? 'Разовая услуга' : 'Разовый товар';
                if (name) name.value = '';
                if (qty) qty.value = '1';
                if (price) price.value = '';
                if (costInput) costInput.value = '';
                resetItemsSelection();
                if (name) name.focus();
            }

            if (openSvc) openSvc.addEventListener('click', ()=>open('service'));
            if (openPart) openPart.addEventListener('click', ()=>open('part'));

            if (cancelBtn) cancelBtn.addEventListener('click', ()=>{
                oneTimeMode = null;
                if (form) form.style.display = 'none';
            });

            if (addBtn) addBtn.addEventListener('click', async ()=>{
                try {
                    if (!oneTimeMode) return;
                    const n = (name?.value || '').trim();
                    const q = parseInt(qty?.value || '1', 10) || 1;
                    const pr = parseFloat((price?.value || '').replace(',', '.'));
                    const costRaw = (costInput?.value || '').toString().replace(',', '.').trim();
                    const cost = costRaw === '' ? null : parseFloat(costRaw);
                    if (!n) { showToast('Введите название', 'warning'); return; }
                    if (!q || q < 1) { showToast('Количество должно быть >= 1', 'warning'); return; }
                    if (!pr || pr <= 0) { showToast('Укажите цену', 'warning'); return; }
                    if (cost !== null && (isNaN(cost) || cost < 0)) { showToast('Некорректная себестоимость', 'warning'); return; }

                    const costParam = oneTimeMode === 'service' ? { cost_price: cost } : { purchase_price: cost };
                    const data = await postAddItem({ type: oneTimeMode, id: null, name: n, quantity: q, price: pr, ...costParam });
                    if (oneTimeMode === 'service' && data.services && data.services.length) {
                        const last = data.services[data.services.length - 1];
                        appendOrderItemToPage('service', { id: last.id, name: last.service_name || n, quantity: last.quantity || q, price: last.price != null ? last.price : pr, cost_price: last.cost_price ?? cost });
                    } else if (oneTimeMode === 'part' && data.order_part_id != null) {
                        appendOrderItemToPage('part', { id: data.order_part_id, name: n, quantity: q, price: pr, purchase_price: cost });
                    } else {
                        appendOrderItemToPage(oneTimeMode, { name: n, quantity: q, price: pr, cost: cost, cost_price: cost, purchase_price: cost });
                    }
                    bumpHistory({ type: oneTimeMode, id: null, name: n, price: pr });
                    showToast('Добавлено', 'success');
                    markItemsAdded(n);
                    afterSuccessfulItemsAdd();
                } catch (e) {
                    console.error(e);
                    showToast(e.message || 'Не удалось добавить', 'error', 'Ошибка');
                }
            });
        })();

        // Обработчик сохранения товара или услуги (выбранная позиция из справочника)
        const saveItemBtn = document.getElementById('saveItemBtn');
        if (saveItemBtn) {
            saveItemBtn.addEventListener('click', async function() {
                // Проверяем, что выбран элемент
                if (!selectedItem || !selectedItem.id) {
                    showToast('Выберите товар или услугу', 'warning');
                    return;
                }
                
                const itemType = selectedItem.type;
                const itemId = selectedItem.id;
                const itemName = selectedItem.name;
                const qtyInput = document.getElementById('selectedItemQtyInput');
                const priceInput = document.getElementById('selectedItemPriceInput');
                const costInput = document.getElementById('selectedItemCostInput');
                const warrantyInput = document.getElementById('selectedItemWarrantyInput');
                const discountInput = document.getElementById('selectedItemDiscountInput');
                const executorSelect = document.getElementById('selectedItemExecutorSelect');
                const quantity = qtyInput ? (parseInt(qtyInput.value, 10) || 1) : 1;
                const priceValueRaw = priceInput ? priceInput.value : '';
                const priceOverride = priceValueRaw !== '' ? parseFloat(String(priceValueRaw).replace(',', '.')) : null;
                const defaultPrice = selectedItem.price || 0;
                const inputPrice = priceOverride !== null && !Number.isNaN(priceOverride) ? priceOverride : defaultPrice;
                const basePrice = inputPrice; // скидка/наценка считается от текущей цены (для заявки)
                const costOverride = costInput && costInput.value !== '' ? parseFloat(String(costInput.value).replace(',', '.')) : null;
                const warrantyDays = warrantyInput && warrantyInput.value !== '' ? parseInt(warrantyInput.value, 10) : null;
                const discountVal = discountInput && discountInput.value !== '' ? parseFloat(String(discountInput.value).replace(',', '.')) : null;
                const executorId = executorSelect && executorSelect.value ? parseInt(executorSelect.value, 10) : null;

                // итоговая цена (unit): базовая цена из справочника/склада + скидка/наценка
                let itemPrice = inputPrice;
                if (discountVal !== null && Number.isFinite(discountVal)) {
                    if (discountType === 'percent') {
                        itemPrice = basePrice * (1 - discountVal / 100.0);
                    } else {
                        itemPrice = basePrice - discountVal;
                    }
                    if (itemPrice < 0) itemPrice = 0;
                }

                if (quantity < 1) {
                    showToast('Количество должно быть >= 1', 'warning');
                        return;
                    }
                if (itemPrice < 0) {
                    showToast('Цена должна быть >= 0', 'warning');
                        return;
                }

                try {
                    // строгий контроль остатков (запрет). Пропускаем проверку при fromCache — данные могли устареть, бэкенд проверит
                    if (itemType === 'part' && !selectedItem.fromCache && selectedItem.stock !== null && selectedItem.stock !== undefined) {
                        const stock = Number(selectedItem.stock);
                        if (Number.isFinite(stock)) {
                            if (stock <= 0) {
                                showToast('Нет остатка. Добавьте через приход склада.', 'error', 'Склад');
                                return;
                            }
                            if (quantity > stock) {
                                showToast(`Недостаточно на складе: есть ${stock} шт.`, 'error', 'Склад');
                                return;
                            }
                        }
                    }

                    const orderId = numericOrderId();
                    if (!orderId) {
                        showToast('Не удалось определить заявку', 'error');
                        return;
                    }
                    const endpoint = itemType === 'service' 
                        ? `/api/orders/${orderId}/services`
                        : `/api/orders/${orderId}/parts`;
                    const payload = itemType === 'service'
                        ? {
                            service_id: itemId,
                            quantity,
                            price: itemPrice,
                            base_price: basePrice,
                            cost_price: costOverride,
                            discount_type: discountVal !== null ? (discountType === 'percent' ? 'percent' : 'amount') : null,
                            discount_value: discountVal,
                            warranty_days: warrantyDays,
                            executor_id: executorId
                        }
                        : {
                            part_id: itemId,
                            quantity,
                            price: itemPrice,
                            base_price: basePrice,
                            purchase_price: costOverride,
                            discount_type: discountVal !== null ? (discountType === 'percent' ? 'percent' : 'amount') : null,
                            discount_value: discountVal,
                            warranty_days: warrantyDays,
                            executor_id: executorId
                        };
                    const resp = await fetch(endpoint, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(payload)
                    });
                    const data = await resp.json();

                    if (data.success) {
                        // Обновляем суммы заявки, если они есть в ответе
                        if (data.order_total !== undefined) {
                            updateOrderTotals(
                                data.order_total || 0,
                                data.order_paid || 0,
                                data.order_debt || 0,
                                data.prepayment || 0,
                                data.overpayment || 0
                            );
                        }
                        // Сразу показываем добавленную позицию в списке на странице
                        if (itemType === 'service' && data.services && data.services.length) {
                            const last = data.services[data.services.length - 1];
                            appendOrderItemToPage('service', { id: last.id, name: last.service_name || itemName, quantity: last.quantity || quantity, price: last.price != null ? last.price : itemPrice, cost_price: last.cost_price ?? costOverride });
                        } else if (itemType === 'part' && data.order_part_id != null) {
                            appendOrderItemToPage('part', { id: data.order_part_id, name: itemName, quantity, price: itemPrice, purchase_price: costOverride });
                        }
                        const itemTypeName = itemType === 'service' ? 'услуга' : 'товар';
                        showToast(`${itemTypeName === 'услуга' ? 'Услуга' : 'Товар'} успешно ${itemType === 'service' ? 'добавлена' : 'добавлен'}`, 'success');
                        bumpHistory({ type: itemType, id: itemId, name: itemName, price: itemPrice, stock_quantity: selectedItem.stock });
                        markItemsAdded(itemName);
                        afterSuccessfulItemsAdd();
                    } else {
                        showToast(data.error || 'Не удалось добавить товар/услугу', 'error', 'Ошибка');
                    }
                } catch (error) {
                    console.error('Ошибка при добавлении товара/услуги:', error);
                    showToast('Произошла ошибка при добавлении товара/услуги', 'error', 'Ошибка');
                }
            });
        }
        // ===== КОНЕЦ ПОИСКА В МОДАЛЬНОМ ОКНЕ "ДОБАВИТЬ ТОВАР ИЛИ УСЛУГУ" =====

        // Функция форматирования даты в формат ДД.ММ.ГГГГ ЧЧ:ММ:СС
        function formatDate(dateStr) {
            if (!dateStr) return '—';
            try {
                // Пробуем разные форматы
                const date = new Date(dateStr);
                if (isNaN(date.getTime())) {
                    // Если не удалось распарсить, пробуем взять первые 10 символов (YYYY-MM-DD)
                    const datePart = dateStr.substring(0, 10);
                    const parts = datePart.split('-');
                    if (parts.length === 3) {
                        // Проверяем, есть ли время в исходной строке
                        const timeMatch = dateStr.match(/(\d{2}):(\d{2}):(\d{2})/);
                        if (timeMatch) {
                            return `${parts[2]}.${parts[1]}.${parts[0]} ${timeMatch[0]}`;
                        }
                        return `${parts[2]}.${parts[1]}.${parts[0]}`;
                    }
                    return dateStr;
                }
                const day = String(date.getDate()).padStart(2, '0');
                const month = String(date.getMonth() + 1).padStart(2, '0');
                const year = date.getFullYear();
                const hours = String(date.getHours()).padStart(2, '0');
                const minutes = String(date.getMinutes()).padStart(2, '0');
                const seconds = String(date.getSeconds()).padStart(2, '0');
                return `${day}.${month}.${year} ${hours}:${minutes}:${seconds}`;
            } catch (e) {
                return dateStr;
            }
        }

        // Функция обновления сумм заявки
        function updateOrderTotals(orderTotal, orderPaid, orderDebt, prepayment = 0, overpayment = 0) {
            console.log('Обновление сумм:', {orderTotal, orderPaid, orderDebt, prepayment, overpayment});
            
            // Обновляем элемент с data-order-debt (блок "К доплате" в summary-card)
            const debtDataEl = document.querySelector('[data-order-debt]');
            if (debtDataEl) {
                const debtTitleEl = document.getElementById('orderDebtTitle');
                const debtHintEl = document.getElementById('orderDebtHint');
                debtDataEl.setAttribute('data-order-debt-value', String(orderDebt));
                debtDataEl.style.color = orderDebt > 0 ? '#ef4444' : '#22c55e';

                if (orderDebt > 0) {
                    debtDataEl.textContent = orderDebt.toFixed(2) + ' ' + ((window.nikaMoneySymbol && window.nikaMoneySymbol()) || '₽');
                    if (debtTitleEl) debtTitleEl.textContent = 'К доплате';
                    if (debtHintEl) debtHintEl.textContent = 'Необходимо доплатить';
                } else if (overpayment > 0) {
                    debtDataEl.textContent = '+' + overpayment.toFixed(2) + ' ' + ((window.nikaMoneySymbol && window.nikaMoneySymbol()) || '₽');
                    if (debtTitleEl) debtTitleEl.textContent = 'Баланс оплаты';
                    if (debtHintEl) debtHintEl.textContent = 'Переплата по заявке';
                } else {
                    debtDataEl.textContent = '0.00 ' + ((window.nikaMoneySymbol && window.nikaMoneySymbol()) || '₽');
                    if (debtTitleEl) debtTitleEl.textContent = 'Баланс оплаты';
                    if (debtHintEl) debtHintEl.textContent = 'Оплата закрыта';
                }

                // Обновляем стиль родительской summary-card
                const summaryCard = debtDataEl.closest('.summary-card');
                if (summaryCard) {
                    const iconEl = document.getElementById('orderDebtIcon');
                    if (orderDebt > 0) {
                        summaryCard.style.background = 'linear-gradient(135deg, rgba(239, 68, 68, 0.1) 0%, rgba(220, 38, 38, 0.05) 100%)';
                        summaryCard.style.borderLeftColor = '#ef4444';
                        if (iconEl) {
                            iconEl.className = 'fas fa-exclamation-triangle me-1';
                        }
                    } else {
                        summaryCard.style.background = 'linear-gradient(135deg, rgba(34, 197, 94, 0.1) 0%, rgba(22, 163, 74, 0.05) 100%)';
                        summaryCard.style.borderLeftColor = '#22c55e';
                        if (iconEl) {
                            iconEl.className = 'fas fa-check-double me-1';
                        }
                    }
                }
                console.log('Обновлено: data-order-debt =', orderDebt.toFixed(2));
            }

            const paidDataEl = document.querySelector('[data-order-paid]');
            if (paidDataEl) {
                paidDataEl.textContent = orderPaid.toFixed(2) + ' ' + ((window.nikaMoneySymbol && window.nikaMoneySymbol()) || '₽');
            }
            const paidPercentEl = document.getElementById('orderPaidPercent');
            if (paidPercentEl) {
                if (orderTotal > 0) {
                    const rawPercent = (orderPaid / orderTotal) * 100;
                    const cappedPercent = Math.min(100, Math.round(rawPercent));
                    paidPercentEl.textContent = cappedPercent + '% от суммы';
                } else {
                    paidPercentEl.textContent = '—';
                }
            }
            
            const totalElements = document.querySelectorAll('.info-item');
            totalElements.forEach(el => {
                const label = el.querySelector('.info-label');
                if (label) {
                    const labelText = label.textContent || label.innerText || '';
                    // Убираем иконки и лишние символы для сравнения
                    const cleanLabelText = labelText.replace(/[^\w\s:]/g, '').trim();
                    
                    if (cleanLabelText.includes('К оплате') || cleanLabelText.includes('Общая сумма')) {
                        const totalEl = el.querySelector('.text-primary') || el.querySelector('.fw-bold.text-primary');
                        if (totalEl) {
                            totalEl.textContent = orderTotal.toFixed(2) + ' ' + ((window.nikaMoneySymbol && window.nikaMoneySymbol()) || '₽');
                            console.log('Обновлено: К оплате =', orderTotal.toFixed(2));
                        }
                    } else if (cleanLabelText.includes('Предоплата')) {
                        const prepaymentEl = el.querySelector('.text-info') || el.querySelector('.fw-bold.text-info');
                        if (prepaymentEl) {
                            prepaymentEl.textContent = prepayment.toFixed(2) + ' ' + ((window.nikaMoneySymbol && window.nikaMoneySymbol()) || '₽');
                            console.log('Обновлено: Предоплата =', prepayment.toFixed(2));
                        }
                    } else if (cleanLabelText.includes('Оплачено')) {
                        const paidEl = el.querySelector('.text-success') || el.querySelector('.fw-bold.text-success');
                        if (paidEl) {
                            paidEl.textContent = orderPaid.toFixed(2) + ' ' + ((window.nikaMoneySymbol && window.nikaMoneySymbol()) || '₽');
                            console.log('Обновлено: Оплачено =', orderPaid.toFixed(2));
                        }
                    } else if (cleanLabelText.includes('К доплате') || cleanLabelText.includes('Задолженность')) {
                        // Ищем элемент с классом fw-bold внутри info-item
                        const debtEl = el.querySelector('.fw-bold');
                        if (debtEl) {
                            debtEl.textContent = orderDebt.toFixed(2) + ' ' + ((window.nikaMoneySymbol && window.nikaMoneySymbol()) || '₽');
                            debtEl.className = 'fw-bold ' + (orderDebt > 0 ? 'text-danger' : 'text-success');
                            console.log('Обновлено: К доплате =', orderDebt.toFixed(2));
                        } else {
                            console.warn('Не найден элемент для "К доплате" в:', el);
                        }
                    }
                }
            });
        }

        // Функция обновления списка оплат
        function updatePaymentsList(payments, orderTotal, orderPaid, orderDebt, prepayment = 0, overpayment = 0) {
            const paymentsList = document.getElementById('paymentsList') ||
                document.getElementById('paymentsListContainer');
            
            // Обновляем суммы через updateOrderTotals
            updateOrderTotals(orderTotal, orderPaid, orderDebt, prepayment, overpayment);
            
            // Обновляем суммы (старый код для совместимости)
            const totalElements = document.querySelectorAll('.info-item');
            totalElements.forEach(el => {
                const label = el.querySelector('.info-label');
                if (label) {
                    const labelText = label.textContent || '';
                    if (labelText.includes('К оплате:') || labelText.includes('Общая сумма:')) {
                        const totalEl = el.querySelector('.text-primary') || el.querySelector('.fw-bold');
                        if (totalEl) {
                            totalEl.textContent = orderTotal.toFixed(2) + ' ' + ((window.nikaMoneySymbol && window.nikaMoneySymbol()) || '₽');
                        }
                    } else if (labelText.includes('Предоплата:')) {
                        const prepaymentEl = el.querySelector('.text-info') || el.querySelector('.fw-bold');
                        if (prepaymentEl) {
                            prepaymentEl.textContent = prepayment.toFixed(2) + ' ' + ((window.nikaMoneySymbol && window.nikaMoneySymbol()) || '₽');
                        }
                    } else if (labelText.includes('Оплачено:')) {
                        const paidEl = el.querySelector('.text-success') || el.querySelector('.fw-bold');
                        if (paidEl) {
                            paidEl.textContent = orderPaid.toFixed(2) + ' ' + ((window.nikaMoneySymbol && window.nikaMoneySymbol()) || '₽');
                        }
                    } else if (labelText.includes('К доплате:') || labelText.includes('Задолженность:')) {
                        const debtEl = el.querySelector('.fw-bold');
                        if (debtEl) {
                            debtEl.textContent = orderDebt.toFixed(2) + ' ' + ((window.nikaMoneySymbol && window.nikaMoneySymbol()) || '₽');
                            debtEl.className = 'fw-bold ' + (orderDebt > 0 ? 'text-danger' : 'text-success');
                        }
                    } else if (labelText.includes('Переплата:')) {
                        const overpaymentEl = el.querySelector('.fw-bold');
                        if (overpaymentEl) {
                            overpaymentEl.textContent = overpayment.toFixed(2) + ' ' + ((window.nikaMoneySymbol && window.nikaMoneySymbol()) || '₽');
                            overpaymentEl.className = 'fw-bold ' + (overpayment > 0 ? 'text-success' : 'text-muted');
                        }
                    }
                }
            });

            // Обновляем таблицу оплат
            if (payments.length === 0) {
                DOMUtils.clear(paymentsList);
                const emptyP = DOMUtils.createElement('p', 'Пока нет оплат', {
                    'class': 'text-muted text-center mb-0'
                });
                paymentsList.appendChild(emptyP);
                return;
            }

            let tableHTML = `
                <div class="table-responsive">
                    <table class="table table-sm table-hover">
                        <thead>
                            <tr>
                                <th>Дата</th>
                                <th>Сумма</th>
                                <th>Тип оплаты</th>
                                <th>Автор</th>
                                <th>Комментарий</th>
                                <th>Действия</th>
                            </tr>
                        </thead>
                        <tbody>
            `;

            const canRefundPayments = !!(window.NIKA_ORDER_PAGE && window.NIKA_ORDER_PAGE.canRefundPayments);
            payments.forEach(payment => {
                const isRefund = (payment.kind || '').toLowerCase() === 'refund';
                const paymentTypeBadge = {
                    'cash': `<span class="badge ${isRefund ? 'bg-danger' : 'bg-success'}">Наличные</span>`,
                    'card': `<span class="badge ${isRefund ? 'bg-danger' : 'bg-primary'}">Карта</span>`,
                    'transfer': `<span class="badge ${isRefund ? 'bg-danger' : 'bg-info'}">Перевод</span>`
                }[payment.payment_type] || `<span class="badge ${isRefund ? 'bg-danger' : 'bg-secondary'}">${payment.payment_type}</span>`;

                const amountStr = isRefund
                    ? `<span class="text-decoration-line-through text-danger fw-bold">−${parseFloat(payment.amount).toFixed(2)} ${((window.nikaMoneySymbol && window.nikaMoneySymbol()) || '₽')}</span> <span class="badge bg-danger ms-1">ВОЗВРАТ</span>`
                    : `${parseFloat(payment.amount).toFixed(2)} ${((window.nikaMoneySymbol && window.nikaMoneySymbol()) || '₽')} ${payment.kind === 'deposit' ? '<span class="badge bg-info text-dark ms-1">предоплата</span>' : ''}`;

                const actionsBtns = isRefund ? '' : `
                            <button class="btn btn-sm btn-outline-secondary receipt-payment-btn"
                                    data-payment-id="${payment.id}"
                                    title="Сформировать чек">
                                <i class="fas fa-receipt"></i>
                            </button>
                            ${canRefundPayments ? `<button class="btn btn-sm btn-outline-warning refund-payment-btn"
                                    data-payment-id="${payment.id}"
                                    data-payment-amount="${payment.amount}"
                                    title="Возврат">
                                <i class="fas fa-undo"></i>
                            </button>` : ''}`;

                tableHTML += `
                    <tr class="${isRefund ? 'table-danger' : ''}">
                        <td>${formatDate(payment.payment_date)}</td>
                        <td class="fw-bold">${amountStr}</td>
                        <td>${paymentTypeBadge}</td>
                        <td>${payment.created_by_username || 'Система'}</td>
                        <td class="${isRefund ? 'text-danger' : ''}">${payment.comment || '—'}</td>
                        <td>${actionsBtns}</td>
                    </tr>
                `;
            });

            tableHTML += `
                        </tbody>
                    </table>
                </div>
            `;

            DOMUtils.setSafeHTML(paymentsList, tableHTML);
        }

        // Создание чека (manual) и печать (capture-phase)
        document.addEventListener('click', async function(e) {
            const btn = e.target.closest('.receipt-payment-btn');
            if (!btn) return;
            e.preventDefault();
            e.stopPropagation();
            const paymentId = btn.getAttribute('data-payment-id');
            if (!paymentId) {
                console.error('Не найден data-payment-id для чека');
                return;
            }

            try {
                const response = await fetch(`/api/payments/${paymentId}/receipts`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ receipt_type: 'sell' })
                });
                const data = await response.json();
                if (!data.success) {
                    showToast(data.error || 'Не удалось сформировать чек', 'error', 'Ошибка');
                    return;
                }
                const receiptId = data.receipt_id;
                window.open(`/receipts/${receiptId}/print`, '_blank');
            } catch (err) {
                console.error('Ошибка при создании чека:', err);
                showToast('Произошла ошибка при создании чека', 'error', 'Ошибка');
            }
        }, true);

        // Возврат по оплате (capture-phase)
        document.addEventListener('click', async function(e) {
            const btn = e.target.closest('.refund-payment-btn');
            if (!btn) return;
            e.preventDefault();
            e.stopPropagation();
            const paymentId = btn.getAttribute('data-payment-id');
            const maxAmount = parseFloat(btn.getAttribute('data-payment-amount') || '0') || 0;
            if (!paymentId) {
                console.error('Не найден data-payment-id для возврата');
                return;
            }

            const amountStr = prompt(`Сумма возврата (макс ${maxAmount.toFixed(2)}):`, maxAmount.toFixed(2));
            if (!amountStr) return;
            const amount = parseFloat(amountStr.replace(',', '.'));
            if (!amount || amount <= 0) {
                showToast('Введите корректную сумму возврата', 'warning');
                return;
            }
            const reason = prompt('Причина возврата (обязательно):', 'Возврат клиенту');
            if (!reason || !reason.trim()) return;

            try {
                const resp = await fetch(`/api/payments/${paymentId}/refund`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ amount, reason: reason.trim(), create_receipt: true })
                });
                const data = await resp.json();
                if (!data.success) {
                    showToast(data.error || 'Не удалось выполнить возврат', 'error', 'Ошибка');
                    return;
                }

                // Обновляем список оплат/суммы
                updatePaymentsList(data.payments, data.order_total, data.order_paid, data.order_debt, data.prepayment || 0, data.overpayment || 0);
                showToast('Возврат выполнен', 'success');

                if (data.receipt_id) {
                    window.open(`/receipts/${data.receipt_id}/print`, '_blank');
                }
            } catch (err) {
                console.error('Ошибка возврата:', err);
                showToast('Произошла ошибка при возврате', 'error', 'Ошибка');
            }
        }, true);

        // Функции для работы с контактами
        function showPhoneMenu(event, phone) {
            event.stopPropagation();
            const menuId = 'phoneMenu-' + phone;
            const menu = document.getElementById(menuId);
            
            // Закрываем все другие меню
            document.querySelectorAll('.contact-dropdown').forEach(m => {
                if (m.id !== menuId) {
                    m.classList.remove('show');
                }
            });
            
            // Переключаем текущее меню
            if (menu) {
                menu.classList.toggle('show');
            }
        }

        // Закрытие меню при клике вне его
        document.addEventListener('click', function(event) {
            if (!event.target.closest('.contact-item')) {
                document.querySelectorAll('.contact-dropdown').forEach(menu => {
                    menu.classList.remove('show');
                });
            }
        });

        // copyToClipboard уже определена выше в начале скрипта
