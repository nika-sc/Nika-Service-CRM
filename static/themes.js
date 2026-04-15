// Система переключения тем
(function() {
    const themes = ['light', 'dark', 'retro'];
    const storedTheme = localStorage.getItem('theme');
    let currentTheme = themes.includes(storedTheme) ? storedTheme : 'light';
    let themeObserver = null;

    function initThemeSwitcher() {
        // Защита от повторной инициализации на случай повторного подключения скрипта.
        if (document.querySelector('.theme-switcher')) {
            return;
        }

        // Создаём блок переключения темы
        const switcher = document.createElement('div');
        switcher.className = 'theme-switcher';
        switcher.innerHTML = `
            <button data-theme="light" class="theme-btn ${currentTheme === 'light' ? 'active' : ''}" title="Светлая тема">
                <i class="fas fa-sun"></i><span class="theme-btn-text">Светлая</span>
            </button>
            <button data-theme="dark" class="theme-btn ${currentTheme === 'dark' ? 'active' : ''}" title="Тёмная тема">
                <i class="fas fa-moon"></i><span class="theme-btn-text">Тёмная</span>
            </button>
        `;

        // Пытаемся встроить переключатель в Mac-меню (справа)
        const macActions = document.querySelector('.mac-menu-container .mac-menu-actions');
        if (macActions) {
            macActions.prepend(switcher);
        } else {
            // Фолбэк: закреплённый в правом верхнем углу (например, на странице логина)
            document.body.appendChild(switcher);
        }

        // Обработчики кликов
        switcher.querySelectorAll('.theme-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                const theme = this.getAttribute('data-theme');
                setTheme(theme);
            });
        });
    }

    function setTheme(theme) {
        const safeTheme = themes.includes(theme) ? theme : 'light';
        applyThemeClasses(safeTheme);
        currentTheme = safeTheme;
        localStorage.setItem('theme', safeTheme);
        updateThemeMeta(safeTheme);
        updateThemeButtons(safeTheme);
        applyTableTheme(safeTheme);
    }

    function applyThemeClasses(theme) {
        themes.forEach(t => {
            document.body.classList.remove(`theme-${t}`);
            document.documentElement.classList.remove(`theme-${t}`);
        });
        document.body.classList.add(`theme-${theme}`);
        document.documentElement.classList.add(`theme-${theme}`);
    }

    function getThemeFromElement(el) {
        if (!el || !el.classList) return null;
        for (const t of themes) {
            if (el.classList.contains(`theme-${t}`)) {
                return t;
            }
        }
        return null;
    }

    function updateThemeMeta(theme) {
        const themeMeta = document.querySelector('meta[name="theme-color"]');
        if (!themeMeta) return;
        const themeColorMap = {
            dark: '#1a1a1a',
            light: '#ecf0f5',
            retro: '#ff1493'
        };
        themeMeta.setAttribute('content', themeColorMap[theme] || '#007bff');
    }

    function updateThemeButtons(theme) {
        document.querySelectorAll('.theme-btn').forEach(btn => {
            btn.classList.remove('active');
            if (btn.getAttribute('data-theme') === theme) {
                btn.classList.add('active');
            }
        });
    }

    function applyTableTheme(theme) {
        // Применяем только к Bootstrap-таблицам, чтобы не ломать печатные/кастомные таблицы.
        document.querySelectorAll('table.table').forEach(table => {
            if (theme === 'dark') {
                table.classList.add('table-dark');
            } else {
                table.classList.remove('table-dark');
            }
        });
    }

    function syncThemeFromBodyClass() {
        const bodyTheme = getThemeFromElement(document.body);
        const safeTheme = themes.includes(bodyTheme) ? bodyTheme : currentTheme;
        currentTheme = safeTheme;
        // Если тему сменили вне switcher (например, сторонним скриптом), синхронизируем <html>.
        themes.forEach(t => document.documentElement.classList.remove(`theme-${t}`));
        document.documentElement.classList.add(`theme-${safeTheme}`);
        localStorage.setItem('theme', safeTheme);
        updateThemeMeta(safeTheme);
        updateThemeButtons(safeTheme);
        applyTableTheme(safeTheme);
    }

    function setupThemeObserver() {
        if (themeObserver || !document.body) {
            return;
        }
        themeObserver = new MutationObserver(mutations => {
            let shouldRefreshTables = false;
            let shouldSyncTheme = false;
            for (const mutation of mutations) {
                if (mutation.type === 'attributes' && mutation.target === document.body && mutation.attributeName === 'class') {
                    shouldSyncTheme = true;
                    continue;
                }
                if (mutation.type === 'childList' && mutation.addedNodes.length) {
                    for (const node of mutation.addedNodes) {
                        if (node.nodeType !== Node.ELEMENT_NODE) continue;
                        if (node.matches?.('table.table') || node.querySelector?.('table.table')) {
                            shouldRefreshTables = true;
                            break;
                        }
                    }
                }
            }

            if (shouldSyncTheme) {
                syncThemeFromBodyClass();
                return;
            }
            if (shouldRefreshTables) {
                applyTableTheme(currentTheme);
            }
        });
        themeObserver.observe(document.body, {
            attributes: true,
            attributeFilter: ['class'],
            childList: true,
            subtree: true
        });
    }

    // Инициализация при загрузке
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() {
            initThemeSwitcher();
            setTheme(currentTheme);
            setupThemeObserver();
        });
    } else {
        initThemeSwitcher();
        setTheme(currentTheme);
        setupThemeObserver();
    }
})();



