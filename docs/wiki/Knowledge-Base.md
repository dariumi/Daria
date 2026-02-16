# Knowledge Base

Локальная база знаний Даши работает по принципу `local-first`:

- сначала ищет релевантные фрагменты в `docs/wiki/*.md`;
- затем в `docs/knowledge/*.{md,txt}`;
- добавляет найденные сниппеты в контекст ответа как factual fallback.

## API

- `GET /api/knowledge/search?q=...&limit=5` — ручной поиск по базе.
- `GET /api/senses/providers` — текущие провайдеры зрения/слуха.
- `POST /api/senses/providers` — выбор провайдеров:
  - `vision_provider`: `auto` | `basic` | `blip`
  - `audio_provider`: `auto` | `whisper` | `hf_asr` | `google_sr`

## Как расширять базу

1. Добавляй markdown-файлы в `docs/knowledge`.
2. Пиши заголовок и короткие секции по теме.
3. Избегай слишком длинных «простыней» в одном файле, лучше разбивать по темам.

## Примечание

Индекс знаний обновляется автоматически и кэшируется на короткий интервал, чтобы не нагружать UI.
