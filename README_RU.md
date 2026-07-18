# PinMazon Local — Pin Studio + Pin Publisher

Локальный Windows-конвейер для подготовки Pinterest affiliate-контента. Milestone A+B работает без OpenAI API и не скрапит Amazon.

Основная цепочка:

`Products → Pin Studio → Review Table → Ready Queue → Pin Publisher`

На этом этапе Publisher ничего не публикует. Он только показывает очередь, прошедшую проверки.

## Что работает сейчас

### Pin Studio — `studio_app.py`

- создание кампаний до 100 creatives;
- ручной ввод товара с реальным фото;
- импорт CSV и XLSX;
- автоматическое добавление Amazon tracking tag из `.env`;
- Product Review и ручное одобрение;
- no-API Template copy provider;
- три угла: result, problem/solution, audience/use-case;
- локальный Pillow renderer, итог строго 1000×1500;
- batch resume без повторной генерации готовых строк;
- Review Table, редактирование текста/доски и локальный re-render;
- массовое Approve / Reject / Send to ready;
- CSV export.

### Pin Publisher — `publisher_app.py`

- читает ту же SQLite-базу;
- показывает только очередь `ready` / `queued`;
- экспортирует ready queue в CSV;
- не открывает Pinterest и не публикует автоматически.

### Сохранён старый режим

Старое приложение `streamlit_app.py` и веб-версия FastAPI не удалены. Generate only продолжает работать. Веб-версия также имеет ручной режим `ChatGPT Plus — no API`: скопировать prompt → получить JSON в ChatGPT → вставить JSON → отрендерить PNG.

## Почему «тема → программа сама находит товары» пока ограничена

Без Amazon Creators API / PA API нельзя безопасно и стабильно получать название, фото и характеристики только по теме или Amazon URL. PinMazon намеренно не читает HTML Amazon. Сейчас тема создаёт кампанию, а товары добавляются вручную или импортируются из CSV/XLSX с проверенными данными и реальным изображением.

## Размещение на диске E

Рекомендуемый путь:

```text
E:\PinMazon\
  studio_app.py
  publisher_app.py
  pinmazon_core\
  data\
    pinmazon.sqlite3
    assets\products\
    assets\creatives\
    browser_profiles\pinterest\
    debug\
```

Если код находится не на E, можно оставить его в другом месте, а данные перенести через `.env`:

```env
PINMAZON_DATA_DIR=E:\PinMazonData
```

## Установка на Windows

```bat
setup_windows.bat
```

Для полностью локального Milestone B `OPENAI_API_KEY` и Pinterest credentials не нужны. Для автоматического affiliate URL добавь в `.env`:

```env
AMAZON_TRACKING_ID=your-tag-20
```

## Запуск двух приложений

Открой два окна:

```bat
run_studio_windows.bat
run_publisher_windows.bat
```

Или вручную:

```bat
.venv\Scripts\activate
streamlit run studio_app.py --server.port 8501
streamlit run publisher_app.py --server.port 8502
```

- Pin Studio: `http://localhost:8501`
- Pin Publisher: `http://localhost:8502`

## Рабочий порядок

1. В Studio создай кампанию и укажи реальные Pinterest boards.
2. Добавь товары вручную или импортируй CSV/XLSX.
3. В Product Review проверь фото, affiliate URL, факты и risk flags.
4. Approve только проверенные товары.
5. В Generate Batch выбери кампанию и товары, запусти generation/resume.
6. В Review Table отредактируй текст/board, нажми Approve selected.
7. Нажми Send selected to ready.
8. Открой Publisher и проверь ready queue.

## Quality gates перед `ready`

Creative блокируется, если:

- нет PNG или размер не 1000×1500;
- нет affiliate disclosure;
- Amazon URL без tracking tag;
- board или alt text пустые;
- headline и bullets не проходят лимиты;
- есть цена, скидка, rating/review claims или aggressive CTA;
- есть critical risk flags;
- creative не был вручную одобрен.

## Формат импорта

Поддерживаются CSV/XLSX колонки:

- `Product`
- `Product URL`
- `Affiliate URL`
- `Image URL` — только прямая PNG/JPG/WEBP ссылка
- `Local Image`
- `Category`
- `Audience`
- `Verified Facts`
- `Score`

## Проверка разработчиком

```bat
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv\Scripts\python.exe -m pytest -q
```

## Что ещё не реализовано

- автоматический поиск/импорт товаров через Amazon Creators API / PA API;
- Ollama и OpenAI copy providers в batch-режиме;
- GPT Image hybrid backgrounds;
- scheduler и дневные лимиты;
- Playwright persistent profile;
- реальная публикация и screenshots/stop conditions;
- Pinterest Analytics CSV и winner variations.

## Milestone C

Следующий этап: официальный copy-provider adapter, Hybrid GPT Image только для фона, счётчик API-вызовов и более глубокий resume. До подтверждения официальных API credentials текущие вызовы не меняются.
