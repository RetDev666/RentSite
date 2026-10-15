from saunacore import create_app
from saunacore.service import DEMO_EMAIL, DEMO_PASSWORD

app = create_app()

if __name__ == "__main__":
    print("Saunacore:  http://127.0.0.1:5050")
    print("Admin:      http://127.0.0.1:5050/admin")
    print(f"Login:      {DEMO_EMAIL} / {DEMO_PASSWORD}")
    app.run(host="127.0.0.1", port=5050, debug=True)
