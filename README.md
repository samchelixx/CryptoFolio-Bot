# 🪙 CryptoFolio Bot

Привет! Это мой opensource пет-проект — Telegram-бот для трекинга криптовалютного портфеля. 

Я написал его, потому что мне не хватало простого и быстрого инструмента прямо в телеге (без платных подписок и перегруженных приложух). Бот умеет считать PnL по каждой монете, строить красивые графики, присылать алерты на нужную цену и даже симулировать стратегии DCA.
![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)
![Aiogram](https://img.shields.io/badge/Aiogram-3.x-blue?logo=telegram)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-red?logo=sqlalchemy)
![CoinGecko](https://img.shields.io/badge/CoinGecko-API-green)

---

## 🚀 Возможности

### 💼 Управление портфелем
- Добавление/продажа криптоактивов
- Автоматический расчёт средней цены покупки
- История всех транзакций
- Множественные портфели

### 📈 Отслеживание цен
- Real-time цены через CoinGecko API
- `/price BTC` — моментальная проверка
- Watchlist для быстрого мониторинга
- Тренды и Топ-15 монет по капитализации

### 📊 Аналитика и графики
- **Pie chart** — распределение портфеля
- **P&L chart** — прибыль/убыток по каждому активу
- **Line chart** — история цены с градиентом и маркерами min/max
- **Candlestick** — свечной график
- Все графики в тёмной теме с premium-дизайном

### 🔔 Ценовые алерты
- Уведомления при достижении целевой цены
- Настройка направления (выше/ниже)
- Автоматическая проверка через APScheduler

### 📐 DCA Калькулятор
- Симуляция Dollar Cost Averaging на исторических данных
- Сравнение DCA vs Lump Sum
- Визуализация результатов

### ⚙️ Настройки
- Валюта отображения: USD, EUR, RUB

---

## 🏗️ Архитектура

```
cryptofolio_bot/
├── run.py                    # Entry point
├── requirements.txt
├── .env.example
└── bot/
    ├── config.py             # Settings from .env
    ├── database/
    │   ├── models.py         # 6 SQLAlchemy models
    │   └── crud.py           # CRUD operations
    ├── handlers/
    │   ├── start.py          # /start, main menu
    │   ├── portfolio.py      # Portfolio CRUD
    │   ├── tracking.py       # Prices, watchlist
    │   ├── alerts.py         # Price alerts
    │   ├── analytics.py      # Charts
    │   ├── dca.py            # DCA calculator
    │   └── settings.py       # User preferences
    ├── keyboards/
    │   └── inline.py         # 15+ inline keyboards
    ├── middlewares/
    │   ├── throttling.py     # Rate limiting
    │   └── database.py       # Session injection
    ├── services/
    │   ├── coingecko.py      # API client + cache
    │   ├── portfolio_service.py  # P&L calculations
    │   ├── chart_service.py  # Matplotlib charts
    │   ├── alert_service.py  # Alert monitoring
    │   └── dca_service.py    # DCA simulation
    ├── states/
    │   └── states.py         # FSM states
    └── utils/
        └── formatters.py     # Text & emoji formatters
```

---

## ⚡ Технологии

| Технология | Назначение |
|------------|------------|
| **aiogram 3.x** | Async Telegram Bot framework |
| **SQLAlchemy 2.0** | ORM с async-поддержкой |
| **aiosqlite** | Async SQLite driver |
| **CoinGecko API** | Real-time крипто данные (бесплатно) |
| **matplotlib** | Генерация графиков |
| **APScheduler** | Фоновые задачи (алерты) |
| **FSM** | Multi-step диалоги |

---

## 🛠️ Установка и запуск

```bash
# 1. Клонируй репозиторий
git clone https://github.com/your-username/cryptofolio-bot.git
cd cryptofolio-bot

# 2. Создай виртуальное окружение
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows

# 3. Установи зависимости
pip install -r requirements.txt

# 4. Настрой переменные окружения
cp .env.example .env
# Отредактируй .env — добавь BOT_TOKEN от @BotFather

# 5. Запусти бота
python run.py
```

---

## 📝 Лицензия

MIT License — используй свободно.
