# 🚀 Інструкція з публікації сайту (Saunacore)

У цьому репозиторії вже налаштовано все необхідне для розгортання як на **Netlify** (`netlify.app`), так і на **Render** (рекомендований варіант для Python/Flask).

---

## 📌 Важлива різниця між платформами

| Параметр | Netlify (`*.netlify.app`) | Render.com (`*.onrender.com`) |
|---|---|---|
| **Тип платформи** | Serverless / Jamstack | Native Python Web Service |
| **Як запускається** | Через Netlify Functions (`serverless-wsgi`) | Постійний сервер через `gunicorn run:app` |
| **База даних (SQLite)** | Працює у `/tmp` (stateless, скидається при холодному рестарті) | Зберігається на сервері / Persistent Disk |
| **Рекомендація** | Підходить для демонстрації / портфоліо | **Найкраще для повноцінної роботи сайту та замовлень** |

---

## 🌐 Варіант 1 — Публікація на Netlify (як ви просили)

Для Netlify у проєкті вже створено:
* `netlify.toml` — інструкція збірки статичних файлів і маршрутизації
* `netlify/functions/app.py` — Serverless WSGI-адаптер для Flask
* `requirements.txt` — додано `serverless-wsgi`

### Крок 1. Завантажити код на GitHub

1. Відкрийте термінал у папці проєкту (`C:\SRC\CarApp`) та виконайте:
   ```bash
   git init
   git add .
   git commit -m "feat: prepare project for Netlify and Render deployment"
   ```
2. Створіть новий репозиторій на [GitHub](https://github.com/new) (наприклад, `carapp-sauna`).
3. Прив'яжіть та відправте код:
   ```bash
   git remote add origin https://github.com/ВАШ_КОРИСТУВАЧ/carapp-sauna.git
   git branch -M main
   git push -u origin main
   ```

---

### Крок 2. Підключення до Netlify

1. Перейдіть на [app.netlify.com](https://app.netlify.com/) та увійдіть у свій акаунт.
2. Натисніть **Add new site** → **Import an existing project**.
3. Оберіть **GitHub** та знайдіть свій репозиторій `carapp-sauna`.
4. Налаштування збірки будуть автоматично підтягнуті з `netlify.toml`:
   - **Build command:** `mkdir -p public && cp -r static public/ && pip install -r requirements.txt`
   - **Publish directory:** `public`
   - **Functions directory:** `netlify/functions`
5. Перейдіть до **Site configuration** → **Environment variables** і додайте:
   - `PYTHON_VERSION`: `3.11`
   - `SAUNACORE_SECRET`: будь-який довгий випадковий ключ (наприклад: `sauna-secret-prod-2026-key`)
6. Натисніть **Deploy site**.

Через 1-2 хвилини ваш сайт буде доступний за адресою:
`https://<ваша-назва>.netlify.app`

> ⚠️ **Зверніть увагу:** Netlify Functions працюють у режимі serverless. База даних автоматично ініціалізується в каталозі `/tmp`. Для довгострокового зберігання бронювань і змін у панелі адміністратора рекомендується платформа з постійним сервером (Render) або підключення хмарної бази (наприклад, Turso).

---

## ⚡ Варіант 2 — Публікація на Render.com (Рекомендовано для Flask)

Render розроблено спеціально для запуску Python/Flask бекендів, підтримує повноцінний веб-сервер Gunicorn та має безкоштовний тариф.

1. Зареєструйтесь на [render.com](https://render.com/).
2. Натисніть **New +** → **Web Service**.
3. Оберіть ваш GitHub репозиторій.
4. Вкажіть налаштування:
   - **Name:** `saunacore` (або будь-яка інша назва)
   - **Language:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn "run:app" --bind 0.0.0.0:$PORT --workers 2 --threads 4`
5. У розділі **Environment Variables** вкажіть:
   - `PYTHON_VERSION`: `3.11.9`
   - `SAUNACORE_SECRET`: будь-який довгий секретний рядок
6. Натисніть **Create Web Service**.

Сайт одразу почне працювати за посиланням `https://saunacore.onrender.com`.

---

## 🔑 Доступ до панелі керування (Admin Panel)

* **URL адмінки:** `/admin` (наприклад, `https://ваша-назва.netlify.app/admin`)
* **Email:** `admin@saunacore.de`
* **Пароль:** `SaunaAdmin2026!`

У панелі керування можна:
- Переглядати замовлення та бронювання
- Керувати моделями саун, фотографіями та цінами
- Налаштовувати зони доставки та тарифи
- Вносити реквізити компанії, налаштовувати пошту (SMTP) та Stripe
- Створювати промокоди / ваучери
- Завантажувати рахунки-фактури у PDF

---

## 🧪 Чек-лист перевірки після публікації

- [ ] Головна сторінка відкривається: `/`
- [ ] Каталог моделей працює: `/flotte`
- [ ] Сторінка бронювання з інтерактивною картою та розрахунком доставки: `/buchen/model-x`
- [ ] Контактна форма: `/kontakt`
- [ ] Вхід до адмін-панелі: `/admin` (з логіном `admin@saunacore.de`)
