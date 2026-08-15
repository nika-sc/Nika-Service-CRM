(function () {
    window.copyToClipboard = async function (text, event) {
        if (event) {
            event.preventDefault();
            event.stopPropagation();
        }
        try {
            await navigator.clipboard.writeText(text);
            var btn = event ? event.target.closest('button, a') : null;
            if (btn) {
                var originalHTML = btn.innerHTML;
                btn.innerHTML = '<i class="fas fa-check"></i>';
                btn.style.color = '#28a745';
                setTimeout(function () {
                    btn.innerHTML = originalHTML;
                    btn.style.color = '';
                }, 1000);
            } else if (window.showToast) {
                window.showToast('Скопировано в буфер обмена', 'success', null, 2000);
            } else {
                alert('Скопировано: ' + text);
            }
        } catch (err) {
            var textArea = document.createElement('textarea');
            textArea.value = text;
            textArea.style.position = 'fixed';
            textArea.style.left = '-999999px';
            document.body.appendChild(textArea);
            textArea.select();
            try {
                document.execCommand('copy');
                if (window.showToast) {
                    window.showToast('Скопировано в буфер обмена', 'success', null, 2000);
                } else {
                    alert('Скопировано: ' + text);
                }
            } catch (e) {
                if (window.showToast) {
                    window.showToast('Не удалось скопировать. Скопируйте вручную', 'error', 'Ошибка копирования', 5000);
                } else {
                    alert('Не удалось скопировать. Скопируйте вручную: ' + text);
                }
            }
            document.body.removeChild(textArea);
        }
    };
})();
