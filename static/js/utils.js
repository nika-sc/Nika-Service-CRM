/**
 * Утилиты для безопасной работы с DOM и логирования
 * Используется в order_detail.html и других шаблонах
 */

// ===== ЛОГИРОВАНИЕ (только в dev режиме) =====
const Logger = {
    isDev: window.location.hostname === 'localhost' || 
           window.location.hostname === '127.0.0.1' ||
           window.location.hostname === '',
    
    log: function(...args) {
        if (this.isDev) {
            console.log(...args);
        }
    },
    
    error: function(...args) {
        // Ошибки всегда логируем
        console.error(...args);
    },
    
    warn: function(...args) {
        if (this.isDev) {
            console.warn(...args);
        }
    },
    
    info: function(...args) {
        if (this.isDev) {
            console.info(...args);
        }
    }
};

// ===== БЕЗОПАСНАЯ РАБОТА С DOM =====
const DOMUtils = {
    /**
     * Безопасная установка текстового содержимого
     * @param {HTMLElement} element - Элемент
     * @param {string} text - Текст для установки
     */
    setText: function(element, text) {
        if (!element) return;
        element.textContent = text || '';
    },
    
    /**
     * Безопасная установка HTML (только для доверенного контента)
     * Использует textContent для пользовательских данных
     * @param {HTMLElement} element - Элемент
     * @param {string} html - HTML для установки
     * @param {boolean} trusted - Если true, устанавливает как HTML, иначе как текст
     */
    setHTML: function(element, html, trusted = false) {
        if (!element) return;
        if (trusted) {
            element.innerHTML = html || '';
        } else {
            // Для недоверенного контента используем textContent
            element.textContent = html || '';
        }
    },
    
    /**
     * Алиас для setHTML (для обратной совместимости)
     * @param {HTMLElement} element - Элемент
     * @param {string} html - HTML для установки
     * @param {boolean} trusted - Если true, устанавливает как HTML, иначе как текст
     */
    setSafeHTML: function(element, html, trusted = true) {
        Logger.warn('DOMUtils.setSafeHTML() используется. Убедитесь, что HTML генерируется на сервере или санитизирован.');
        this.setHTML(element, html, trusted);
    },
    
    /**
     * Создает элемент option безопасным способом
     * @param {string} value - Значение option
     * @param {string} text - Текст option
     * @param {Object} attributes - Дополнительные атрибуты (data-*)
     * @returns {HTMLOptionElement}
     */
    createOption: function(value, text, attributes = {}) {
        const option = document.createElement('option');
        option.value = value || '';
        option.textContent = text || '';
        
        // Устанавливаем дополнительные атрибуты
        Object.keys(attributes).forEach(key => {
            option.setAttribute(key, attributes[key]);
        });
        
        return option;
    },
    
    /**
     * Очищает содержимое элемента безопасным способом
     * @param {HTMLElement} element - Элемент для очистки
     */
    clear: function(element) {
        if (!element) return;
        while (element.firstChild) {
            element.removeChild(element.firstChild);
        }
    },
    
    /**
     * Создает элемент с текстовым содержимым
     * @param {string} tagName - Имя тега
     * @param {string} text - Текст содержимого
     * @param {Object} attributes - Атрибуты элемента
     * @returns {HTMLElement}
     */
    createElement: function(tagName, text = '', attributes = {}) {
        const element = document.createElement(tagName);
        if (text) {
            element.textContent = text;
        }
        
        Object.keys(attributes).forEach(key => {
            element.setAttribute(key, attributes[key]);
        });
        
        return element;
    }
};

// Экспорт для использования в других скриптах
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { Logger, DOMUtils };
}

