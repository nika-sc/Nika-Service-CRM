# Локальные копии CDN-ресурсов

Все CSS, JS и шрифты загружаются из этой папки, чтобы приложение работало **без доступа к интернету**.

## Обновление ресурсов

Запустите скрипт загрузки из корня проекта:

```bash
python scripts/download_cdn_assets.py
```

Скрипт скачивает в `static/cdn/`:

- **jQuery** 3.6.0  
- **Bootstrap** 5.3.0 (CSS + JS)  
- **Font Awesome** 7.0.0 (CSS + webfonts)  
- **AdminLTE** 3.2 (CSS + JS)  
- **Socket.IO** 4.5.4 (client)  
- **DataTables** 1.13.7 + Buttons, Responsive, ColReorder + ru.json  
- **Tom Select** 2.2.2  
- **Sortable.js** 1.15.2  
- **Chart.js** 4.4.0  

Шаблоны подключают эти файлы через `url_for('static', filename='cdn/...')`.
