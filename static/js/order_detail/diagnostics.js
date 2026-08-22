(function () {
    var currentNumericId = null;
    var pendingStatus = null;
    var savedThisOpen = false;
    var uploadsInFlight = Promise.resolve();
    var templateItems = [];
    var selectedTemplateId = "";

    function csrfToken() {
        return document.querySelector('meta[name="csrf-token"]')?.getAttribute("content") || "";
    }

    function orderId() {
        if (currentNumericId) return currentNumericId;
        if (typeof ORDER_ID !== "undefined") return ORDER_ID;
        return null;
    }

    function statusItem(statusId) {
        if (statusId === undefined || statusId === null || statusId === "") return null;
        return document.querySelector('.status-dropdown-item[data-status-id="' + statusId + '"]');
    }

    function isBlockingStatus(statusId) {
        var item = statusItem(statusId);
        if (!item) return false;
        var blocks = item.dataset.blocksEdit === "1" || item.dataset.blocksEdit === "true";
        var fin = item.dataset.isFinal === "1" || item.dataset.isFinal === "true";
        return blocks || fin;
    }

    function updateDiagnosticsButton(filled) {
        var btn = document.getElementById("openDiagnosticsBtn");
        if (!btn) return;
        btn.setAttribute("data-has-diagnostics", filled ? "1" : "0");
        btn.classList.toggle("btn-success", !!filled);
        btn.classList.toggle("btn-warning", !filled);
        btn.classList.toggle("text-dark", !filled);
        btn.title = filled ? "Открыть диагностику" : "Заполните диагностику до закрытия заявки";
        btn.innerHTML = '<i class="fas fa-stethoscope me-1"></i>' + (filled ? "Диагностика" : "Нужна диагностика");
    }

    function setPendingHint(pending) {
        var hint = document.getElementById("diagnosticsPendingHint");
        if (!hint) return;
        if (pending && pending.statusName) {
            hint.textContent = "После сохранения статус станет: " + pending.statusName;
            hint.classList.remove("d-none");
        } else {
            hint.textContent = "";
            hint.classList.add("d-none");
        }
    }

    function applyAccess(data) {
        var canEdit = !!data.can_edit_text;
        var canUpload = !!data.can_upload;
        var ta = document.getElementById("diagnosticsText");
        var saveBtn = document.getElementById("saveDiagnosticsBtn");
        var fileInput = document.getElementById("diagnosticsFileInput");
        var fileWrap = document.getElementById("diagnosticsFileWrap");
        var hint = document.getElementById("diagnosticsTextHint");
        if (ta) ta.readOnly = !canEdit;
        if (saveBtn) saveBtn.classList.toggle("d-none", !canEdit);
        var tplWrap = document.getElementById("diagnosticsTemplateWrap");
        var tplSearch = document.getElementById("diagnosticsTemplateSearch");
        if (tplSearch) tplSearch.disabled = !canEdit;
        if (tplWrap) tplWrap.classList.toggle("d-none", !canEdit || !templateItems.length);
        if (fileInput) fileInput.disabled = !canUpload;
        if (fileWrap) fileWrap.classList.toggle("d-none", !canUpload);
        if (hint) {
            if (!canEdit && data.order_locked) {
                hint.textContent = "Заявка закрыта: текст и файлы может менять только администратор.";
            } else if (!canEdit && data.text_set) {
                hint.textContent = "Текст уже сохранён. Изменить его может только администратор. Фото может добавить сотрудник, удалить — только администратор.";
            } else {
                hint.textContent = "После сохранения текст может изменить только администратор. Без текста нельзя закрыть заявку.";
            }
        }
        window._diagnosticsCanDelete = !!data.can_delete_files;
        var filled = !!(data.diagnostics && String(data.diagnostics).trim());
        updateDiagnosticsButton(filled);
    }

    function escapeHtml(s) {
        return String(s || "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;");
    }

    function renderFiles(files) {
        var box = document.getElementById("diagnosticsFilesList");
        if (!box) return;
        if (!files || !files.length) {
            box.textContent = "Файлов нет";
            return;
        }
        var canDelete = !!window._diagnosticsCanDelete;
        box.innerHTML = files.map(function (f) {
            var url = "/api/order/" + orderId() + "/diagnostics/files/" + f.id;
            var isImg = String(f.mime_type || "").indexOf("image/") === 0;
            var preview = isImg
                ? '<img src="' + url + '" alt="" style="max-width:96px;max-height:96px;object-fit:cover;border-radius:6px;margin-right:8px;">'
                : '<i class="fas fa-file-pdf me-2"></i>';
            var del = canDelete
                ? '<button type="button" class="btn btn-sm btn-outline-danger" data-file-id="' + f.id + '">Удалить</button>'
                : "";
            return '<div class="d-flex align-items-center justify-content-between border rounded p-2 mb-2">'
                + '<a href="' + url + '" target="_blank" rel="noopener">' + preview + escapeHtml(f.filename || "файл") + "</a>"
                + del
                + "</div>";
        }).join("");
        box.querySelectorAll("[data-file-id]").forEach(function (btn) {
            btn.addEventListener("click", function () {
                deleteFile(btn.getAttribute("data-file-id"));
            });
        });
    }

    function renderHistory(history) {
        var box = document.getElementById("diagnosticsHistoryList");
        if (!box) return;
        if (!history || !history.length) {
            box.textContent = "Записей нет";
            return;
        }
        box.innerHTML = history.map(function (h) {
            var when = escapeHtml(h.created_at || "");
            var who = escapeHtml(h.author || "сотрудник");
            var body = escapeHtml(h.body || "");
            return '<div class="border rounded p-2 mb-2 bg-light">'
                + '<div class="text-muted mb-1">' + when + " · " + who + "</div>"
                + '<div style="white-space:pre-wrap;">' + body + "</div>"
                + "</div>";
        }).join("");
    }

    function showModal() {
        var el = document.getElementById("diagnosticsModal");
        if (el && window.bootstrap && window.bootstrap.Modal) {
            window.bootstrap.Modal.getOrCreateInstance(el).show();
        }
    }

    function closeModal() {
        var el = document.getElementById("diagnosticsModal");
        if (el && window.bootstrap && window.bootstrap.Modal) {
            var inst = window.bootstrap.Modal.getInstance(el);
            if (inst) inst.hide();
        }
    }

    function applyDiagnosticsTemplateText(current, body) {
        return String(body || "").replace(/\r\n/g, "\n").replace(/^\n+|\n+$/g, "");
    }

    function templateSearchInput() {
        return document.getElementById("diagnosticsTemplateSearch");
    }

    function templateListEl() {
        return document.getElementById("diagnosticsTemplateList");
    }

    function selectedTemplate() {
        if (!selectedTemplateId) return null;
        for (var i = 0; i < templateItems.length; i++) {
            if (String(templateItems[i].id) === String(selectedTemplateId)) return templateItems[i];
        }
        return null;
    }

    function normalizeTemplateQuery(s) {
        return String(s || "").toLowerCase().trim();
    }

    function filteredTemplates(query) {
        var q = normalizeTemplateQuery(query);
        if (!q) return templateItems.slice();
        return templateItems.filter(function (item) {
            return normalizeTemplateQuery(item.name).indexOf(q) !== -1
                || normalizeTemplateQuery(item.body).indexOf(q) !== -1;
        });
    }

    function closeTemplateList() {
        var list = templateListEl();
        var input = templateSearchInput();
        if (list) list.classList.remove("show");
        if (input) input.setAttribute("aria-expanded", "false");
    }

    function showSelectedTemplateName() {
        var input = templateSearchInput();
        if (!input) return;
        var item = selectedTemplate();
        input.value = item && item.name ? item.name : "";
    }

    function renderTemplateList(query) {
        var list = templateListEl();
        var input = templateSearchInput();
        if (!list || !input || input.disabled) return;
        var items = filteredTemplates(query);
        if (!items.length) {
            list.innerHTML = '<span class="dropdown-item-text text-muted small">Ничего не найдено</span>';
        } else {
            list.innerHTML = items.map(function (item) {
                var id = String(item.id);
                var active = id === String(selectedTemplateId) ? " active" : "";
                return '<button type="button" class="dropdown-item text-wrap' + active + '" role="option" data-template-id="'
                    + escapeHtml(id) + '">' + escapeHtml(item.name || ("Шаблон #" + id)) + "</button>";
            }).join("");
            list.querySelectorAll("[data-template-id]").forEach(function (btn) {
                btn.addEventListener("mousedown", function (e) {
                    e.preventDefault();
                    pickTemplate(btn.getAttribute("data-template-id"));
                });
            });
        }
        list.classList.add("show");
        input.setAttribute("aria-expanded", "true");
    }

    function pickTemplate(id) {
        var item = null;
        for (var i = 0; i < templateItems.length; i++) {
            if (String(templateItems[i].id) === String(id)) {
                item = templateItems[i];
                break;
            }
        }
        if (!item) return;
        var ta = document.getElementById("diagnosticsText");
        if (!ta || ta.readOnly) return;
        selectedTemplateId = String(item.id);
        showSelectedTemplateName();
        ta.value = applyDiagnosticsTemplateText(ta.value, item.body || "");
        closeTemplateList();
    }

    function fillTemplateSelect(items) {
        templateItems = items || [];
        selectedTemplateId = "";
        var wrap = document.getElementById("diagnosticsTemplateWrap");
        var input = templateSearchInput();
        var ta = document.getElementById("diagnosticsText");
        var canShow = !!(ta && !ta.readOnly && templateItems.length);
        if (wrap) wrap.classList.toggle("d-none", !canShow);
        if (input) {
            input.value = "";
            input.disabled = !canShow;
        }
        closeTemplateList();
    }

    function templateQueryForList(input) {
        var item = selectedTemplate();
        if (item && input.value === item.name) return "";
        return input.value;
    }

    function moveTemplateHighlight(delta) {
        var list = templateListEl();
        if (!list || !list.classList.contains("show")) return;
        var btns = Array.prototype.slice.call(list.querySelectorAll("[data-template-id]"));
        if (!btns.length) return;
        var idx = -1;
        btns.forEach(function (b, i) {
            if (b.classList.contains("active")) idx = i;
        });
        if (idx < 0) idx = delta > 0 ? -1 : 0;
        idx = (idx + delta + btns.length) % btns.length;
        btns.forEach(function (b, i) { b.classList.toggle("active", i === idx); });
        if (btns[idx] && btns[idx].scrollIntoView) btns[idx].scrollIntoView({ block: "nearest" });
    }

    function pickHighlightedTemplate() {
        var list = templateListEl();
        if (!list) return;
        var active = list.querySelector("[data-template-id].active") || list.querySelector("[data-template-id]");
        if (active) pickTemplate(active.getAttribute("data-template-id"));
    }

    function loadTemplateOptions(data) {
        var params = new URLSearchParams({ match: "1" });
        if (data && data.device_type_id) params.set("type_id", data.device_type_id);
        if (data && data.device_brand_id) params.set("brand_id", data.device_brand_id);
        if (data && data.model_id) params.set("model_id", data.model_id);
        return fetch("/api/diagnostics-templates?" + params.toString(), { credentials: "same-origin" })
            .then(function (r) { return r.json(); })
            .then(function (items) {
                fillTemplateSelect(Array.isArray(items) ? items : []);
            })
            .catch(function () { fillTemplateSelect([]); });
    }

    function loadDiagnostics(opts) {
        opts = opts || {};
        var preserveDraft = !!opts.preserveDraft;
        var id = orderId();
        if (!id) return Promise.resolve(null);
        if (!preserveDraft) {
            templateItems = [];
            selectedTemplateId = "";
            showSelectedTemplateName();
            closeTemplateList();
        }
        var ta = document.getElementById("diagnosticsText");
        var draft = preserveDraft && ta ? ta.value : null;
        return fetch("/api/order/" + id + "/diagnostics", { credentials: "same-origin" })
            .then(function (r) { return r.json(); })
            .then(function (data) {
                if (!data || !data.success) return data;
                if (ta) {
                    if (draft !== null) ta.value = draft;
                    else ta.value = data.diagnostics || "";
                }
                applyAccess(data);
                if (preserveDraft && ta && draft !== null) ta.value = draft;
                renderFiles(data.files || []);
                renderHistory(data.history || []);
                if (!preserveDraft) {
                    loadTemplateOptions(data);
                }
                return data;
            })
            .catch(function () { return null; });
    }

    function saveText() {
        var id = orderId();
        var ta = document.getElementById("diagnosticsText");
        var snapshot = ta ? String(ta.value) : "";
        var body = snapshot.trim();
        var saveBtn = document.getElementById("saveDiagnosticsBtn");
        if (saveBtn) saveBtn.disabled = true;
        uploadsInFlight
            .catch(function () { return null; })
            .then(function () {
                return fetch("/api/order/" + id + "/diagnostics", {
                    method: "PUT",
                    credentials: "same-origin",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": csrfToken(),
                    },
                    body: JSON.stringify({ diagnostics: snapshot }),
                });
            })
            .then(function (r) { return r.json().then(function (data) { return { ok: r.ok, data: data }; }); })
            .then(function (res) {
                var data = res.data || {};
                if (typeof showToast === "function") {
                    showToast(data.success ? "Диагностика сохранена" : (data.error || "Ошибка"), data.success ? "success" : "error");
                }
                if (!data.success) return;
                updateDiagnosticsButton(!!body);
                if (pendingStatus) {
                    if (!body) {
                        if (typeof showToast === "function") {
                            showToast("Сначала заполните диагностику", "warning");
                        }
                        return;
                    }
                    savedThisOpen = true;
                    var pending = pendingStatus;
                    pendingStatus = null;
                    closeModal();
                    if (window.updateOrderStatus) {
                        window.updateOrderStatus(
                            pending.buttonElement,
                            pending.orderId,
                            pending.orderDbId,
                            pending.statusId,
                            pending.statusName,
                            pending.statusColor,
                            pending.statusCode
                        );
                    }
                    return;
                }
                savedThisOpen = true;
                closeModal();
            })
            .catch(function () {})
            .then(function () {
                if (saveBtn) saveBtn.disabled = false;
            });
    }

    function uploadFile(file) {
        var id = orderId();
        var form = new FormData();
        form.append("file", file);
        return fetch("/api/order/" + id + "/diagnostics/files", {
            method: "POST",
            credentials: "same-origin",
            headers: { "X-CSRFToken": csrfToken() },
            body: form,
        })
            .then(function (r) { return r.json(); })
            .then(function (data) {
                if (!data.success && typeof showToast === "function") {
                    showToast((file && file.name ? file.name + ": " : "") + (data.error || "Не удалось загрузить файл"), "error");
                }
                return data;
            })
            .catch(function () { return { success: false }; });
    }

    function deleteFile(fileId) {
        var id = orderId();
        fetch("/api/order/" + id + "/diagnostics/files/" + fileId, {
            method: "DELETE",
            credentials: "same-origin",
            headers: { "X-CSRFToken": csrfToken() },
        })
            .then(function (r) { return r.json(); })
            .then(function (data) {
                if (!data.success && typeof showToast === "function") {
                    showToast(data.error || "Не удалось удалить файл", "error");
                }
                loadDiagnostics({ preserveDraft: true });
            })
            .catch(function () {});
    }

    function openForOrder(numericId, options) {
        options = options || {};
        currentNumericId = numericId;
        pendingStatus = options.pendingStatus || null;
        savedThisOpen = false;
        setPendingHint(pendingStatus);
        loadDiagnostics();
        showModal();
    }

    function restorePendingButton() {
        if (!pendingStatus) return;
        var p = pendingStatus;
        var btn = p.buttonElement;
        if (!btn) return;
        var name = btn.dataset.originalStatusName;
        var color = btn.dataset.originalStatusColor;
        var sid = btn.dataset.originalStatusId;
        if (name) btn.textContent = name;
        if (color) {
            btn.style.backgroundColor = color;
            btn.style.borderColor = color;
        }
        if (sid !== undefined) btn.dataset.statusId = sid;
        btn.disabled = false;
        btn.style.opacity = "1";
    }

    function guardStatusChange(opts) {
        opts = opts || {};
        var numericId = opts.numericId;
        var statusId = opts.statusId;
        var restore = typeof opts.restore === "function" ? opts.restore : restorePendingButton;
        if (!isBlockingStatus(statusId)) {
            return Promise.resolve(true);
        }
        if (!numericId) {
            return Promise.resolve(true);
        }
        return fetch("/api/order/" + numericId + "/diagnostics", { credentials: "same-origin" })
            .then(function (r) { return r.json(); })
            .then(function (data) {
                var text = data && data.diagnostics ? String(data.diagnostics).trim() : "";
                if (text) return true;
                if (typeof restore === "function") restore();
                openForOrder(numericId, {
                    pendingStatus: {
                        buttonElement: opts.buttonElement,
                        orderId: opts.orderId,
                        orderDbId: opts.orderDbId || numericId,
                        statusId: opts.statusId,
                        statusName: opts.statusName,
                        statusColor: opts.statusColor,
                        statusCode: opts.statusCode,
                    },
                });
                return false;
            })
            .catch(function () { return true; });
    }

    window.NikaDiagnostics = {
        openForOrder: openForOrder,
        guardStatusChange: guardStatusChange,
        isBlockingStatus: isBlockingStatus,
        isMissingDiagnosticsError: function (msg) {
            return String(msg || "").indexOf("Сначала заполните диагностику") !== -1;
        },
    };

    document.addEventListener("DOMContentLoaded", function () {
        var openBtn = document.getElementById("openDiagnosticsBtn");
        var saveBtn = document.getElementById("saveDiagnosticsBtn");
        var fileInput = document.getElementById("diagnosticsFileInput");
        var modal = document.getElementById("diagnosticsModal");
        if (openBtn) {
            openBtn.addEventListener("click", function () {
                var id = (typeof ORDER_ID !== "undefined") ? ORDER_ID : currentNumericId;
                openForOrder(id, {});
            });
        }
        if (saveBtn) saveBtn.addEventListener("click", saveText);
        var tplSearch = templateSearchInput();
        if (tplSearch) {
            tplSearch.addEventListener("focus", function () {
                if (tplSearch.disabled) return;
                renderTemplateList(templateQueryForList(tplSearch));
            });
            tplSearch.addEventListener("input", function () {
                renderTemplateList(tplSearch.value);
            });
            tplSearch.addEventListener("keydown", function (e) {
                if (e.key === "Escape") {
                    e.preventDefault();
                    closeTemplateList();
                    showSelectedTemplateName();
                    return;
                }
                if (e.key === "ArrowDown") {
                    e.preventDefault();
                    if (!templateListEl() || !templateListEl().classList.contains("show")) {
                        renderTemplateList(templateQueryForList(tplSearch));
                    }
                    moveTemplateHighlight(1);
                    return;
                }
                if (e.key === "ArrowUp") {
                    e.preventDefault();
                    moveTemplateHighlight(-1);
                    return;
                }
                if (e.key === "Enter") {
                    e.preventDefault();
                    pickHighlightedTemplate();
                }
            });
            tplSearch.addEventListener("blur", function () {
                setTimeout(function () {
                    closeTemplateList();
                    showSelectedTemplateName();
                }, 120);
            });
        }
        if (fileInput) {
            fileInput.addEventListener("change", function () {
                var picked = fileInput.files ? Array.prototype.slice.call(fileInput.files) : [];
                fileInput.value = "";
                if (!picked.length) return;
                var chain = uploadsInFlight.catch(function () { return null; });
                picked.forEach(function (file) {
                    chain = chain.then(function () { return uploadFile(file); });
                });
                uploadsInFlight = chain.then(function () {
                    return loadDiagnostics({ preserveDraft: true });
                });
            });
        }
        if (modal) {
            modal.addEventListener("hidden.bs.modal", function () {
                if (!savedThisOpen) {
                    restorePendingButton();
                }
                pendingStatus = null;
                savedThisOpen = false;
                setPendingHint(null);
            });
        }
    });
})();
