from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
import sqlite3 as sq
import datetime as dt
import threading
import time

ACCOUNT_SID = "AC01ba2d70ed0aa5f87b9199a5b3652954"
AUTH_TOKEN = "be26603df2e98420187771f1f8caf9e5"
FROM_NUMBER = "whatsapp:+14155238886"
client = Client(ACCOUNT_SID, AUTH_TOKEN)

app = Flask(__name__)

def init_db():
    with sq.connect("chatbot.db") as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS BIRTHDAYS (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender TEXT,
                name TEXT,
                date TEXT NOT NULL
            )
        """)
        conn.commit()

def save_data(user_id, name, date):
    with sq.connect("chatbot.db") as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO BIRTHDAYS (sender, name, date) VALUES (?, ?, ?)",
            (user_id, name, date)
        )
        conn.commit()

def get_data(user_id):
    with sq.connect("chatbot.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name, date FROM BIRTHDAYS WHERE sender = ?", (user_id,))
        return cursor.fetchall()

@app.route("/", methods=["POST"])
def bot():
    user_msg = request.values.get("Body", "").strip()
    sender = request.values.get("From")
    profile_name = request.values.get("ProfileName", "User")

    print(f"📩 Message from {profile_name} ({sender}): {user_msg}")

    resp = MessagingResponse()
    msg = resp.message()

    if user_msg.lower().startswith("add"):
        try:
            parts = user_msg.split(" ")
            if len(parts) < 3:
                raise ValueError("Invalid format")
            name = parts[1]
            date_str = parts[2]
            dt.datetime.strptime(date_str, "%d-%m-%Y")
            save_data(sender, name, date_str)
            msg.body(f"✅ Saved birthday for {name} on {date_str}")
        except Exception:
            msg.body("❌ Error! Format:\nadd Name dd-mm-yyyy\nExample: add John 09-08-2005")

    elif user_msg.lower() == "show":
        data = get_data(sender)
        if data:
            result = "\n".join([f"{name} 🎉 on {date}" for name, date in data])
            msg.body("📅 Your saved birthdays:\n" + result)
        else:
            msg.body("📭 No birthdays found!")

    else:
        msg.body(
            "👋 Welcome to Birthday Bot!\n\n"
            "Commands:\n"
            "• `add Name dd-mm-yyyy` – Save a birthday\n"
            "• `show` – View your saved birthdays"
        )

    return str(resp)

def birthday_reminder_loop():
    while True:
        today_day_month = dt.datetime.now().strftime("%d-%m")
        with sq.connect("chatbot.db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT sender, name, date FROM BIRTHDAYS")
            results = cursor.fetchall()
            for sender, name, date_str in results:
                try:
                    # Extract day and month only from the saved date
                    saved_day_month = dt.datetime.strptime(date_str, "%d-%m-%Y").strftime("%d-%m")
                    if saved_day_month == today_day_month:
                        message = f"🎉 Reminder: Today is {name}'s birthday! 🎂🎉"
                        client.messages.create(
                            body=message,
                            from_=FROM_NUMBER,
                            to=sender
                        )
                        print(f"✅ Sent reminder to {sender} for {name}")
                except Exception as e:
                    print(f"⚠️ Error processing {name}: {e}")
        time.sleep(60)


if __name__ == "__main__":
    init_db()
    reminder_thread = threading.Thread(target=birthday_reminder_loop, daemon=True)
    reminder_thread.start()

    app.run(debug=True)
