# Dasha Scenario Tuning Report (v0.9.2)

## Что сделано
- Добавлен публичный внешний вход генерации:
  - `DariaBrain.generate_external(...)` в `core/brain.py`
- Добавлен API-эндпоинт внешней генерации:
  - `POST /api/chat/external/generate` в `web/app.py`
- Добавлен сценарный раннер:
  - `tests/scenario_runner.py`
- Добавлен анти-дубль для повторов одного и того же ответа подряд.
- Усилены правила естественности:
  - лучшее определение эмоционального контекста (`_analyze`)
  - точнее разделены knowledge-вопросы и бытовой диалог (`_looks_like_knowledge_query`)
  - добавлены естественные шаблоны для:
    - ночной болтовни
    - мягкой поддержки при усталости
    - лёгкого юмора/самоиронии
    - тёплой ответной реакции на поддержку пользователя
  - снижена избыточная инъекция личных трейтов в приветствия/спасибо/прощание

## Новый внешний API
`POST /api/chat/external/generate`

Пример payload:
```json
{
  "source": "telegram",
  "source_chat_id": "chat-42",
  "content": "Привет, ты не спишь?",
  "persist_memory": true,
  "track_attention": false,
  "learn_style": false,
  "schedule_followup": false,
  "save_chat": true,
  "force_fallback": false,
  "random_seed": 123
}
```

Возвращает:
- `response`
- `messages`
- `extra_messages`
- `state`
- `emotion`
- `chat_id` (если `save_chat=true`)

## Сценарный прогон
Команда:
```bash
PYTHONPATH=. python3 tests/scenario_runner.py --force-fallback --seed 123 --out docs/reports/dasha_scenarios_report.json
```

Итог:
- Отчёт: `docs/reports/dasha_scenarios_report.json`
- Все 6 сценариев прошли без flagged-ошибок раннера.
- В ответах убраны:
  - бессвязные склейки
  - неуместные knowledge-вставки в бытовом диалоге
  - «не в тему» автофразы про шаги и служебные формулировки

Дополнительно:
```bash
PYTHONPATH=. python3 tests/scenario_runner.py --seed 123 --out docs/reports/dasha_scenarios_report_live.json
```
- `docs/reports/dasha_scenarios_report_live.json` также показал 6/6 без flagged-ошибок.

## Наблюдение после тюнинга
- Диалог стал заметно ближе к образу «скромной, мягкой подружки».
- Ночные/эмоциональные ветки звучат естественнее.
- Поддержка и юмор чаще попадают в нужный контекст.

## Остаточный риск
- При сильной рандомизации отдельных слоёв могут появляться чуть разные интонации.
- Для production-регрессий стоит закрепить ещё 1-2 seed-прогона в CI и добавить ручной review эталонных диалогов.
