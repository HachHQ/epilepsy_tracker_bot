## ⚙️ Установка и запуск

### Предварительные требования
*   Python 3.10 или выше
*   Токен бота от [@BotFather](https://t.me/BotFather)

### Локальный запуск

1.  **Клонируйте репозиторий:**
    ```bash
    git clone https://github.com/HachHQ/epilepsy_tracker_bot.git
    cd epilepsy_tracker_bot
    ```

2.  **Создайте виртуальное окружение:**
    ```bash
    python -m venv venv
    # Windows
    venv\Scripts\activate
    # Linux/macOS
    source venv/bin/activate
    ```

3.  **Установите зависимости:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Настройте переменные окружения:**
    Создайте файл `.env` на основе `.env.example`:
    ```env
    BOT_TOKEN=ващ_токен_от_BotFather
    DB_NAME=epilepsy_db.sqlite
    ADMIN_IDS=12345678,87654321
    ```

5.  **Запустите бота:**
    ```bash
    python main.py
    ```

### 🐳 Запуск через Docker

```bashz