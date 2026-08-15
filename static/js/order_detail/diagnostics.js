(function () {
    var currentNumericId = null;
    var pendingStatus = null;
    var savedThisOpen = false;

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

    function loadDiagnostics() {
        var id = orderId();
        if (!id) return Promise.resolve(null);
        return fetch("/api/order/" + id + "/diagnostics", { credentials: "same-origin" })
            .then(function (r) { return r.json(); })
            .then(function (data) {
                if (!data || !data.success) return data;
                var ta = document.getElementById("diagnosticsText");
                if (ta) ta.value = data.diagnostics || "";
                applyAccess(data);
                renderFiles(data.files || []);
                renderHistory(data.history || []);
                return data;
            })
            .catch(function () { return null; });
    }

    function saveText() {
        var id = orderId();
        var ta = document.getElementById("diagnosticsText");
        var body = ta ? String(ta.value).trim() : "";
        fetch("/api/order/" + id + "/diagnostics", {
            method: "PUT",
            credentials: "same-origin",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": csrfToken(),
            },
            body: JSON.stringify({ diagnostics: ta ? ta.value : "" }),
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
            .catch(function () {});
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
                loadDiagnostics();
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
        if (fileInput) {
            fileInput.addEventListener("change", function () {
                var picked = fileInput.files ? Array.prototype.slice.call(fileInput.files) : [];
                fileInput.value = "";
                if (!picked.length) return;
                var chain = Promise.resolve();
                picked.forEach(function (file) {
                    chain = chain.then(function () { return uploadFile(file); });
                });
                chain.then(function () { loadDiagnostics(); });
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
