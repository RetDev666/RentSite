# 🚀 Інструкція з публікації сайту (Saunacore)

## ⚠️ Чому Netlify показав «Page Not Found» (404)?

**Netlify не підтримує виконання Python-функцій у своєму безсерверному середовищі** (Netlify Functions підтримує лише **Node.js/JavaScript/TypeScript та Go**). Файли `.py` всередині `netlify/functions` просто ігноруються Netlify, тому веб-сервер не запускається і Netlify повертає помилку 404.

Для розміщення Flask-сайту є два ідеальних та перевірених безкоштовних варіанти:

---

## 🥇 Варіант 1 — Render.com (РЕКОМЕНДОВАНО ДЛЯ FLASK)

**Render** розроблений спеціально для веб-додатків на Python. Тут сайт працює як постійний повноцінний сервер з базою даних SQLite, адмін-панеллю, генерацією PDF та Stripe.

### Як запустити на Render за 2 хвилини:
1. Зареєструйтесь або увійдіть на [render.com](https://render.com/) (можна в 1 клік через GitHub).
2. Натисніть кнопку **New +** → **Web Service**.
3. Оберіть ваш репозиторій **`RetDev666/RentSite`**.
4. Вкажіть параметри:
   * **Name:** `saunacore` (або будь-яка інша назва для вашого піддомену)
   * **Region:** Frankfurt (EU) або будь-який
   * **Branch:** `main`
   * **Language:** `Python 3`
   * **Build Command:** `pip install -r requirements.txt`
   * **Start Command:** `gunicorn "run:app" --bind 0.0.0.0:$PORT --workers 2 --threads 4`
5. У розділі **Environment Variables** додайте:
   * `PYTHON_VERSION`: `3.11.9`
   * `SAUNACORE_SECRET`: будь-який секретний рядок (наприклад `sauna-secret-key-2026`)
6. Оберіть тарифний план **Free** і натисніть **Create Web Service**.

🎉 За 2 хвилини сайт буде доступний за адресою:  
`https://saunacore.onrender.com`

---

## 🥈 Варіант 2 — Vercel.com (прямий аналог Netlify з доменом *.vercel.app)

Якщо ви шукаєте саме швидкий хмарний хостинг, ідентичний до Netlify (з доменом `*.vercel.app`), використовуйте **Vercel**. На відміну від Netlify, **Vercel офіційно та нативно підтримує Python та Flask**!

У репозиторій уже додано всі необхідні файли конфігурації:
* `vercel.json`
* `api/index.py`

### Як запустити на Vercel за 1 хвилину:
1. Зайдіть на [vercel.com](https://vercel.com/) та увійдіть через GitHub.
2. Натисніть **Add New...** → **Project**.
3. Знайдіть репозиторій **`RetDev666/RentSite`** та натисніть **Import**.
4. Натисніть **Deploy** (Vercel сам розпізнає Python через `vercel.json` та `api/index.py`).

🎉 Сайт буде онлайн на:  
`https://rent-site.vercel.app` (або обрана вами назва).

---

## 🔑 Доступ до панелі керування (Admin Panel)

* **URL:** `/admin` (наприклад, `https://ваша-назва.onrender.com/admin`)
* **Email:** `admin@saunacore.de`
* **Пароль:** `SaunaAdmin2026!`
