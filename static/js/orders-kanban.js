(function () {
    var form = document.getElementById("kanbanFiltersForm");
    if (!form) {
        return;
    }

    var cfg = window.NIKA_KANBAN || {};
    var debounceMs = parseInt(cfg.debounceMs, 10);
    if (!debounceMs || debounceMs < 0) {
        debounceMs = 1000;
    }

    var timer = null;
    var lastState = serializeForm();

    function serializeForm() {
        var data = new FormData(form);
        var params = new URLSearchParams();
        data.forEach(function (value, key) {
            if (value) {
                params.append(key, value);
            }
        });
        return params.toString();
    }

    function submitKanban() {
        var next = serializeForm();
        if (next === lastState) {
            return;
        }
        lastState = next;
        var url = new URL(form.getAttribute("action") || "/all_orders", window.location.origin);
        var data = new FormData(form);
        data.forEach(function (value, key) {
            if (value) {
                url.searchParams.set(key, value);
            }
        });
        window.location.href = url.toString();
    }

    function scheduleSubmit() {
        clearTimeout(timer);
        var current = serializeForm();
        if (current === lastState) {
            return;
        }
        timer = setTimeout(submitKanban, debounceMs);
    }

    form.querySelectorAll(".filter-field").forEach(function (field) {
        field.addEventListener("change", scheduleSubmit);
        if (field.matches("input[type='search'], input[type='text']")) {
            field.addEventListener("input", scheduleSubmit);
        }
    });

    form.addEventListener("submit", function () {
        clearTimeout(timer);
    });
})();
