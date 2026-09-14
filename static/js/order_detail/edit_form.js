/* Extracted from templates/order_detail.html — keep in sync with NIKA_ORDER_PAGE bootstrap. */
const editSymptomHidden = document.getElementById('editSymptomTagsInput');
        const editAppearanceHidden = document.getElementById('editAppearanceInput');

        function initEditSelect(selector, hiddenInput, initialString) {
            const instance = new TomSelect(selector, {
                plugins: ['remove_button'],
                persist: false,
                maxItems: 8,
                create: true,
                placeholder: 'Введите или выберите значение'
            });

            const values = initialString
                ? initialString.split(',').map(v => v.trim()).filter(Boolean)
                : [];
            if (values.length) {
                values.forEach(val => {
                    if (!instance.options[val]) {
                        instance.addOption({ value: val, text: val });
                    }
                });
                instance.setValue(values);
            }

            const syncHidden = () => {
                const selected = instance.getValue();
                hiddenInput.value = Array.isArray(selected) ? selected.join(', ') : selected;
            };

            instance.on('change', syncHidden);
            syncHidden();

            return instance;
        }

        initEditSelect('#editSymptomTags', editSymptomHidden, editSymptomHidden.value || '');
        initEditSelect('#editAppearanceTags', editAppearanceHidden, editAppearanceHidden.value || '');
        
        // Инициализация TomSelect для поля "Модель" (как в add_order.html)
        function normalizeTagLabel(label) {
            if (!label || !label.trim()) return null;
            const trimmed = label.trim();
            return trimmed[0].toUpperCase() + trimmed.slice(1);
        }
        
        // Инициализируем TomSelect для модели при открытии модального окна
        const editOrderModal = document.getElementById('editOrderModal');
        if (editOrderModal) {
            // В закрытом статусе модалку можно открыть только в режиме смены исполнителей
            if (window.NIKA_ORDER_PAGE && window.NIKA_ORDER_PAGE.blocksEdit) {
            editOrderModal.addEventListener('show.bs.modal', function(e) {
                const related = e.relatedTarget;
                const assigneesOnly = related && related.getAttribute('data-assignees-only') === '1';
                if (!assigneesOnly) {
                    e.preventDefault();
                    const bsModal = bootstrap.Modal.getInstance(editOrderModal);
                    if (bsModal) bsModal.hide();
                    showToast('Редактирование заявки заблокировано. Можно сменить мастера/менеджера кнопкой «Сменить исполнителей».', 'warning', 'Редактирование заблокировано');
                    return false;
                }
            }, true);
            }
            let tomEditModel = null;

            function setEditOrderAssigneesOnlyMode(enabled) {
                const flag = document.getElementById('assigneesOnlyFlag');
                const title = document.getElementById('editOrderModalLabel');
                const form = document.getElementById('editOrderForm');
                if (flag) flag.value = enabled ? '1' : '0';
                if (title) {
                    const titleOrderId = (window.NIKA_ORDER_PAGE && window.NIKA_ORDER_PAGE.orderId) || window.ORDER_ID || '';
                    title.textContent = enabled
                        ? 'Смена исполнителей заявки #' + titleOrderId
                        : 'Редактирование заявки #' + titleOrderId;
                }
                if (!form) return;
                const keepNames = new Set(['manager', 'master', 'csrf_token', 'assignees_only', 'status']);
                form.querySelectorAll('input, select, textarea, button').forEach(function(el) {
                    if (el.id === 'assigneesOnlyFlag') return;
                    if (el.type === 'hidden' && keepNames.has(el.name)) return;
                    if (el.closest('.modal-footer')) return;
                    if (el.classList.contains('btn-close')) return;
                    const name = el.getAttribute('name') || '';
                    const isAssigneeField = name === 'manager' || name === 'master';
                    if (enabled) {
                        if (!isAssigneeField && el.tagName !== 'BUTTON') {
                            el.dataset.prevDisabled = el.disabled ? '1' : '0';
                            el.disabled = true;
                        } else {
                            el.disabled = false;
                        }
                    } else if (el.dataset.prevDisabled !== undefined) {
                        el.disabled = el.dataset.prevDisabled === '1';
                        delete el.dataset.prevDisabled;
                    }
                });
                // Disabled fields are not submitted — keep assignee selects enabled
                form.querySelectorAll('select[name="manager"], select[name="master"]').forEach(function(sel) {
                    sel.disabled = false;
                });
            }
            
            editOrderModal.addEventListener('show.bs.modal', function(e) {
                const related = e.relatedTarget;
                const assigneesOnly = !!(related && related.getAttribute('data-assignees-only') === '1');
                setEditOrderAssigneesOnlyMode(assigneesOnly);

                const editModelSelect = document.getElementById('editModel');
                if (!editModelSelect || assigneesOnly) return;
                
                // Удаляем старый экземпляр, если есть
                if (tomEditModel) {
                    tomEditModel.destroy();
                    tomEditModel = null;
                }
                
                // Создаем новый экземпляр TomSelect
                tomEditModel = new TomSelect('#editModel', {
                    create: function(input, callback) {
                        const normalized = normalizeTagLabel(input);
                        if (!normalized) return;
                        
                        // Создаем новую модель через API
                        fetch('/api/order-models', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                            },
                            body: JSON.stringify({ name: normalized })
                        })
                        .then(res => res.json())
                        .then(data => {
                            if (data.success) {
                                showToast(`Модель "${normalized}" успешно создана`, 'success', null, 2000);
                                callback({ value: normalized, text: normalized });
                            } else {
                                showToast('Не удалось создать модель', 'warning', null, 2000);
                                callback({ value: normalized, text: normalized });
                            }
                        })
                        .catch(error => {
                            console.error('Ошибка при создании модели:', error);
                            showToast('Ошибка при создании модели', 'error', 'Ошибка', 3000);
                            callback({ value: normalized, text: normalized });
                        });
                    },
                    sortField: {
                        field: 'text',
                        direction: 'asc'
                    },
                    placeholder: 'Выберите или введите модель...',
                    maxOptions: null,
                    hideSelected: false,
                    allowEmptyOption: true,
                    plugins: ['input_autogrow']
                });
                
                // Загружаем существующие модели
                fetch('/api/order-models')
                    .then(res => res.json())
                    .then(models => {
                        if (Array.isArray(models) && tomEditModel) {
                            models.forEach(model => {
                                if (!tomEditModel.options[model.name]) {
                                    tomEditModel.addOption({ value: model.name, text: model.name });
                                }
                            });
                            // Устанавливаем текущее значение модели заявки
                            const currentModel = editModelSelect.getAttribute('data-initial') || '';
                            if (currentModel) {
                                tomEditModel.setValue(currentModel, true);
                            }
                        }
                    })
                    .catch(error => {
                        console.error('Ошибка при загрузке моделей:', error);
                    });
            });
        }
