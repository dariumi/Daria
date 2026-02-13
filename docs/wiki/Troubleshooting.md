# Troubleshooting

## `/api/behavior` возвращает 500

Проверь, что используется версия `0.8.5+`.
В `0.8.5` сохранена обратная совместимость `MoodSystem.get_behavior_hints()`.

## Ошибка в браузере `Cannot set properties of null (textContent)`

Ошибка исправлена в `0.8.5`: загрузка контента окна синхронизирована с инициализацией (`openWindow/createWindow`).

## Плагин voice-call падает с `get_user_profile`

Исправлено в `0.8.5`: метод `PluginAPI.get_user_profile()` добавлен в ядро плагинов.

## Обновление из архива не работает

Проверь:
- путь к архиву корректен;
- архив содержит корень проекта с `VERSION`, `main.py`, `web/`;
- формат архива: `.zip`, `.tar`, `.tar.gz`, `.tgz`.
