/**
 * Глобальный поиск с автодополнением (в навбаре .mac-search-box).
 * Всё в IIFE, чтобы не конфликтовать с переменными на странице заявки (например searchTimeout в order_detail).
 */
(function() {
    'use strict';

    var searchTimeout = null;
    var searchHistory = [];
    var globalSearchInitialized = false;

    try {
        var saved = localStorage.getItem('searchHistory');
        if (saved) {
            searchHistory = JSON.parse(saved);
        }
    } catch (e) {
        console.warn('Не удалось загрузить историю поисков:', e);
    }

    function getNavbarSearchElements() {
        var box = document.querySelector('.mac-search-box');
        if (!box) return { input: null, autocomplete: null, form: null };
        var input = box.querySelector('#globalSearchInput') || document.getElementById('globalSearchInput');
        var autocomplete = box.querySelector('#searchAutocomplete') || document.getElementById('searchAutocomplete');
        var form = input && input.closest('form');
        return { input: input, autocomplete: autocomplete, form: form };
    }

    function escapeHtml(text) {
        var div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function fetchAutocomplete(query) {
        var box = document.querySelector('.mac-search-box');
        var autocomplete = box ? box.querySelector('#searchAutocomplete') : document.getElementById('searchAutocomplete');
        if (!autocomplete) return;

        fetch('/search/api/autocomplete?q=' + encodeURIComponent(query))
            .then(function(res) { return res.json(); })
            .then(function(data) {
                if (data.success) {
                    renderAutocomplete(data.results, query);
                } else {
                    autocomplete.style.display = 'none';
                }
            })
            .catch(function(err) {
                console.error('Ошибка автодополнения:', err);
                autocomplete.style.display = 'none';
            });
    }

    var typeLabels = { order: 'Заявка', customer: 'Клиент', part: 'Товар' };
    var typeIcons = { order: 'fa-file-alt', customer: 'fa-user', part: 'fa-box' };

    function renderAutocomplete(results, query) {
        var box = document.querySelector('.mac-search-box');
        var autocomplete = box ? box.querySelector('#searchAutocomplete') : document.getElementById('searchAutocomplete');
        if (!autocomplete) return;

        var historyItems = searchHistory
            .filter(function(h) { return h.toLowerCase().indexOf(query.toLowerCase()) !== -1 && h !== query; })
            .slice(0, 3)
            .map(function(h) {
                return '<a href="#" class="autocomplete-item autocomplete-history" data-query="' + escapeHtml(h) + '">' +
                    '<span class="autocomplete-item-icon history"><i class="fas fa-history"></i></span>' +
                    '<span class="autocomplete-item-body"><span class="autocomplete-item-title">' + escapeHtml(h) + '</span></span></a>';
            })
            .join('');

        var resultsHtml = results.map(function(item) {
            var icon = typeIcons[item.type] || 'fa-search';
            var label = typeLabels[item.type] || '';
            return '<a href="#" class="autocomplete-item autocomplete-result" data-type="' + item.type + '" data-id="' + escapeHtml(String(item.id)) + '">' +
                '<span class="autocomplete-item-icon ' + item.type + '"><i class="fas ' + icon + '"></i></span>' +
                '<span class="autocomplete-item-body"><span class="autocomplete-item-title">' + escapeHtml(item.text) + '</span></span>' +
                '<span class="autocomplete-item-badge ' + item.type + '">' + escapeHtml(label) + '</span></a>';
        }).join('');

        if (!historyItems && !resultsHtml) {
            autocomplete.style.display = 'none';
            return;
        }
        autocomplete.innerHTML = (historyItems ? '<div class="autocomplete-section"><div class="autocomplete-section-header">История</div>' + historyItems + '</div>' : '') +
            (resultsHtml ? '<div class="autocomplete-section"><div class="autocomplete-section-header">Результаты</div>' + resultsHtml + '</div>' : '');
        autocomplete.style.display = 'block';

        autocomplete.querySelectorAll('.autocomplete-history').forEach(function(item) {
            item.addEventListener('click', function(e) {
                e.preventDefault();
                var q = this.dataset.query;
                var el = getNavbarSearchElements();
                if (el.input) {
                    el.input.value = q;
                    if (el.form) el.form.submit();
                }
            });
        });
    }

    function initGlobalSearch() {
        if (globalSearchInitialized) return;
        var el = getNavbarSearchElements();
        var searchInput = el.input;
        var autocomplete = el.autocomplete;
        var searchForm = el.form;
        if (!searchInput || !autocomplete) return;
        globalSearchInitialized = true;

        searchInput.addEventListener('input', function() {
            var query = this.value.trim();
            clearTimeout(searchTimeout);
            if (query.length < 2) {
                autocomplete.style.display = 'none';
                return;
            }
            searchTimeout = setTimeout(function() {
                fetchAutocomplete(query);
            }, 300);
        });

        document.addEventListener('click', function(e) {
            if (!searchInput.contains(e.target) && !autocomplete.contains(e.target)) {
                autocomplete.style.display = 'none';
            }
        });

        autocomplete.addEventListener('click', function(e) {
            var item = e.target.closest('.autocomplete-item');
            if (item) {
                e.preventDefault();
                var type = item.dataset.type;
                var id = item.dataset.id;
                if (type === 'order') {
                    window.location.href = '/order/' + id;
                } else if (type === 'customer') {
                    window.location.href = '/clients/' + id;
                } else if (type === 'part') {
                    window.location.href = '/warehouse/parts/' + id;
                }
            }
        });

        if (searchForm) {
            searchForm.addEventListener('submit', function() {
                var query = searchInput.value.trim();
                if (query && searchHistory.indexOf(query) === -1) {
                    searchHistory.unshift(query);
                    if (searchHistory.length > 10) searchHistory = searchHistory.slice(0, 10);
                    try {
                        localStorage.setItem('searchHistory', JSON.stringify(searchHistory));
                    } catch (e) {}
                }
            });
        }
    }

    function tryInitGlobalSearch() {
        initGlobalSearch();
        if (!globalSearchInitialized && document.readyState !== 'complete') {
            window.addEventListener('load', function() {
                globalSearchInitialized = false;
                initGlobalSearch();
            }, { once: true });
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', tryInitGlobalSearch);
    } else {
        tryInitGlobalSearch();
    }
    window.addEventListener('load', tryInitGlobalSearch);
})();
