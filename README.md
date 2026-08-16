# Умный суммаризатор тендерной документации

[![CI](https://github.com/KinzelVA/Umnii_summarizator_tender_documents/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/KinzelVA/Umnii_summarizator_tender_documents/actions/workflows/ci.yml)

FastAPI-сервис для автоматического извлечения ключевой информации из PDF-документов государственных закупок с помощью локальной LLM через Ollama.

Сервис принимает PDF и возвращает структурированную выжимку:

- сумму контракта;
- сроки выполнения;
- ключевые требования к исполнителю;
- штрафы и неустойки.

## Возможности

- загрузка PDF через HTTP API;
- проверка MIME-типа, расширения, сигнатуры и размера файла;
- извлечение текстового слоя через `pypdf`;
- анализ документа локальной LLM через Ollama;
- структурированный ответ по JSON Schema;
- валидация результата через Pydantic;
- защита prompt от инструкций внутри анализируемого документа;
- rate limiting для тяжелого endpoint;
- structured JSON logging;
- OpenAPI / Swagger;
- unit- и API-тесты;
- Docker и Docker Compose;
- GitHub Actions CI.

## Стек

- Python 3.11+
- FastAPI
- Pydantic / pydantic-settings
- pypdf
- Ollama Python SDK
- `gpt-oss:20b`
- pytest
- Docker
- Docker Compose
- GitHub Actions

## Архитектура

Основной поток обработки:

    PDF
      |
      v
    FastAPI
      |
      v
    Проверка файла
      |
      v
    PDF extraction
      |
      v
    Нормализация текста
      |
      v
    Ollama / gpt-oss:20b
      |
      v
    JSON Schema
      |
      v
    Pydantic validation
      |
      v
    JSON response

Код разделен по ответственности:

    app/
    ├── api/
    │   └── routes/
    │       ├── health.py
    │       └── summarize.py
    ├── core/
    │   ├── config.py
    │   ├── logging.py
    │   ├── rate_limit.py
    │   └── request_logging.py
    ├── schemas/
    │   ├── health.py
    │   └── summary.py
    ├── services/
    │   ├── llm.py
    │   └── pdf.py
    └── main.py

    tests/
    ├── test_health.py
    ├── test_llm_service.py
    ├── test_logging.py
    ├── test_pdf_service.py
    ├── test_rate_limit.py
    ├── test_summarize_api.py
    └── test_summary_schema.py

    docs/
    └── solution.md

Подробное описание алгоритма и архитектурных решений находится в `docs/solution.md`.

## Формат результата

Успешный ответ `POST /api/v1/summarize` имеет следующую структуру:

    {
      "contract_amount": "256 652.50 RUB",
      "execution_deadlines": "From 16.08.2026 to 31.12.2026",
      "contractor_requirements": [],
      "penalties": []
    }

Если в документе отсутствуют соответствующие сведения:

- `contract_amount` возвращается как `null`;
- `execution_deadlines` возвращается как `null`;
- `contractor_requirements` возвращается как `[]`;
- `penalties` возвращается как `[]`.

## Требования для локального запуска

Необходимо установить:

- Python 3.11 или новее;
- Ollama;
- модель `gpt-oss:20b`.

Проект разрабатывался и тестировался на Python 3.12.

Установка модели Ollama:

    ollama pull gpt-oss:20b

Проверить установленные модели:

    ollama list

Ollama по умолчанию должна быть доступна по адресу:

    http://localhost:11434

## Локальная установка

Клонировать репозиторий:

    git clone https://github.com/KinzelVA/Umnii_summarizator_tender_documents.git
    cd Umnii_summarizator_tender_documents

Создать виртуальное окружение:

Windows PowerShell:

    python -m venv .venv
    .\.venv\Scripts\Activate.ps1

Установить проект вместе с dev-зависимостями:

    python -m pip install --upgrade pip
    python -m pip install -e ".[dev]"

Создать локальный файл конфигурации:

    Copy-Item .env.example .env

Запустить API:

    uvicorn app.main:app --reload

После запуска сервис доступен по адресу:

    http://127.0.0.1:8000

## Swagger / OpenAPI

Swagger UI:

    http://127.0.0.1:8000/docs

OpenAPI schema:

    http://127.0.0.1:8000/openapi.json

Health endpoint:

    GET /health

Пример ответа:

    {
      "status": "ok"
    }

## Использование API

Основной endpoint:

    POST /api/v1/summarize

Запрос отправляется как `multipart/form-data`, поле файла называется `file`.

Пример для Windows PowerShell:

    curl.exe -X POST `
      -F "file=@D:\path\to\tender.pdf;type=application/pdf" `
      http://127.0.0.1:8000/api/v1/summarize

Пример для Linux/macOS:

    curl -X POST \
      -F "file=@/path/to/tender.pdf;type=application/pdf" \
      http://127.0.0.1:8000/api/v1/summarize

## Конфигурация

Настройки загружаются через `pydantic-settings`.

Все переменные окружения имеют префикс `TENDER_`.

Пример находится в `.env.example`.

Основные параметры:

    TENDER_LOG_LEVEL=INFO
    TENDER_MAX_PDF_SIZE_MB=20

    TENDER_OLLAMA_BASE_URL=http://localhost:11434
    TENDER_OLLAMA_MODEL=gpt-oss:20b
    TENDER_OLLAMA_CONTEXT_LENGTH=16384
    TENDER_LLM_TIMEOUT_SECONDS=120

    TENDER_RATE_LIMIT_REQUESTS=10
    TENDER_RATE_LIMIT_WINDOW_SECONDS=60

## Работа с LLM

По умолчанию используется локальная модель:

    gpt-oss:20b

Основные параметры inference:

- temperature: `0`;
- think: `low`;
- context window: `16384`;
- timeout: `120` секунд.

Модель получает JSON Schema, сформированную из Pydantic-модели `TenderSummary`.

System prompt требует использовать только факты из документа и запрещает придумывать отсутствующую информацию.

Содержимое загруженного PDF рассматривается как недоверенные данные: инструкции, обнаруженные внутри документа, не должны изменять поведение модели.

## Работа с PDF

Перед анализом выполняются:

1. проверка расширения и MIME-типа;
2. проверка максимального размера;
3. проверка сигнатуры `%PDF-`;
4. открытие через `pypdf`;
5. проверка на повреждение и шифрование;
6. извлечение текста со всех страниц;
7. нормализация текста.

Максимальный размер по умолчанию:

    20 MB

Текущая версия работает с PDF, содержащими текстовый слой.

OCR для сканированных документов не реализован.

## Коды ответа API

Основные HTTP-статусы:

- `200 OK` — успешная обработка;
- `400 Bad Request` — поврежденный, зашифрованный PDF или отсутствие текстового слоя;
- `413 Content Too Large` — превышен допустимый размер;
- `415 Unsupported Media Type` — файл не является PDF;
- `422 Unprocessable Entity` — некорректный HTTP-запрос;
- `429 Too Many Requests` — превышен rate limit;
- `502 Bad Gateway` — LLM вернула некорректный результат;
- `503 Service Unavailable` — LLM provider недоступен;
- `504 Gateway Timeout` — превышено время ожидания LLM.

Для `429 Too Many Requests` сервис также возвращает заголовок `Retry-After`.

## Rate limiting

Endpoint:

    POST /api/v1/summarize

по умолчанию ограничен:

    10 запросов / 60 секунд / IP

Health endpoint и документация API этим ограничением не затрагиваются.

Текущая реализация хранит состояние rate limiter в памяти одного процесса.

Для production-среды с несколькими workers или экземплярами сервиса логичным развитием будет общий backend, например Redis.

## Structured logging

HTTP-запросы логируются в JSON-формате.

В лог включаются:

- timestamp;
- log level;
- logger;
- HTTP method;
- path;
- status code;
- duration.

Это упрощает дальнейшую передачу логов в централизованные системы наблюдаемости.

## Docker

Собрать image:

    docker build -t tender-document-summarizer:dev .

Запустить контейнер вручную:

    docker run --rm -p 8000:8000 -e TENDER_OLLAMA_BASE_URL=http://host.docker.internal:11434 tender-document-summarizer:dev

Для реального LLM-запроса контейнер должен иметь доступ к запущенной Ollama.

## Docker Compose

Для Windows с Docker Desktop и Ollama, работающей на хосте:

    docker compose up --build -d

Проверить состояние:

    docker compose ps

Проверить health endpoint:

    curl.exe http://127.0.0.1:8000/health

Посмотреть логи:

    docker compose logs api

Остановить:

    docker compose down

В `compose.yaml` Ollama на Windows-хосте доступна контейнеру через:

    http://host.docker.internal:11434

Для Linux-host окружения способ доступа контейнера к Ollama может потребовать дополнительной настройки Docker networking.

Ollama и модель намеренно не включены в Compose: приложение использует отдельно запущенный LLM provider.

## Тестирование

Запустить весь набор:

    python -m pytest -v

Текущий набор:

    34 passed

Тестами покрыты:

- health endpoint;
- PDF extraction;
- ошибки PDF;
- Pydantic-схемы;
- взаимодействие с LLM;
- ошибки LLM;
- endpoint суммаризации;
- HTTP error mapping;
- rate limiting;
- structured logging;
- OpenAPI metadata.

Тестирование LLM не требует установленной или запущенной Ollama: используется fake client.

Кроме автоматических тестов, сервис был проверен end-to-end на реальных PDF-документах ЕИС.

## CI

В `.github/workflows/ci.yml` настроен GitHub Actions pipeline.

Job `Tests`:

1. устанавливает Python 3.12;
2. устанавливает проект и dev-зависимости;
3. запускает pytest.

После него выполняется `Docker smoke test`:

1. проверяет `docker compose config`;
2. собирает Docker image;
3. запускает контейнер;
4. проверяет `GET /health`;
5. удаляет test container.

CI успешно проходит в GitHub Actions.

## Ограничения

Текущая версия сознательно не решает все возможные сценарии тендерной документации.

Основные ограничения:

- OCR отсутствует;
- chunking очень больших документов пока не реализован;
- один запрос обрабатывает один PDF;
- rate limiting является in-memory;
- качество результата зависит от используемой LLM;
- локальная модель на CPU может обрабатывать документ заметное время.

Для больших документов следующим этапом может быть chunking с последующим объединением результатов.

## Возможное дальнейшее развитие

- OCR для сканированных PDF;
- chunking и многошаговый анализ больших документов;
- обработка комплектов документов;
- Redis-backed rate limiting;
- поддержка дополнительных LLM providers;
- метрики и distributed tracing.

## Логика решения

Подробное описание алгоритма, решений и ограничений:

`docs/solution.md`

## Лицензия

Условия использования проекта находятся в файле `LICENSE`.