(function () {
    function request(url, options) {
        var opts = options || {};
        return fetch(url, opts).then(function (res) {
            return res.json()
                .then(function (data) {
                    return { ok: res.ok, status: res.status, data: data };
                })
                .catch(function () {
                    return { ok: res.ok, status: res.status, data: null };
                });
        });
    }

    function get(url) {
        return request(url, { method: 'GET' });
    }

    function sendJson(url, method, payload) {
        return request(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload || {})
        });
    }

    window.OrderDetailApiClient = {
        request: request,
        get: get,
        sendJson: sendJson
    };
})();
