(function () {
    try {
        var stored = localStorage.getItem('theme') || 'light';
        if (['light', 'dark', 'retro'].indexOf(stored) === -1) {
            stored = 'light';
        }
        var root = document.documentElement;
        root.classList.remove('theme-light', 'theme-dark', 'theme-retro');
        root.classList.add('theme-' + stored);
        var themeMeta = document.querySelector('meta[name="theme-color"]');
        if (themeMeta) {
            var themeColorMap = {
                dark: '#1a1a1a',
                light: '#ecf0f5',
                retro: '#ff1493'
            };
            themeMeta.setAttribute('content', themeColorMap[stored] || '#007bff');
        }
    } catch (e) {
        // localStorage may be unavailable
    }
})();
