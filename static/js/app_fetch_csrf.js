(function () {
    function getCsrfToken() {
        var meta = document.querySelector('meta[name="csrf-token"]');
        return meta ? meta.getAttribute('content') : null;
    }

    var originalFetch = window.fetch;
    if (!originalFetch) return;

    window.fetch = function (input, init) {
        init = init || {};
        var method = (init.method || 'GET').toUpperCase();
        var unsafe = ['POST', 'PUT', 'PATCH', 'DELETE'].indexOf(method) !== -1;

        if (unsafe) {
            var token = getCsrfToken();
            if (token) {
                var headers = new Headers(init.headers || {});
                if (!headers.has('X-CSRFToken')) headers.set('X-CSRFToken', token);
                if (!headers.has('X-CSRF-Token')) headers.set('X-CSRF-Token', token);
                init.headers = headers;
            }
            if (!init.credentials) init.credentials = 'same-origin';
        }

        return originalFetch(input, init);
    };
})();
