(function () {
    try {
        var t = localStorage.getItem('theme') || 'light';
        if (['light', 'dark', 'retro'].indexOf(t) === -1) {
            t = 'light';
        }
        document.body.classList.remove('theme-light', 'theme-dark', 'theme-retro');
        document.body.classList.add('theme-' + t);
    } catch (e) {}
})();
