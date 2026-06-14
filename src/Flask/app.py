import requests
from flask import Flask, render_template, redirect, url_for
import os
import sys
from pathlib import Path

# --- THE PATHING FIX ---
# 1. Find our exact location (src/Flask)
current_dir = Path(__file__).resolve().parent
# 2. Go up one level to 'src'
src_dir = current_dir.parent
# 3. Go up one more level to the Project Root ('TG-bot-controller')
project_root = src_dir.parent

# Tell Python to look in BOTH folders when searching for imports like 'env' or 'Bot'
sys.path.append(str(project_root))
sys.path.append(str(src_dir))
# ------------------------

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from env import keys
from Bot.Connector import open_connection
from Bot.QueryManager import QueryManager
app = Flask(__name__)


@app.route('/')
def dashboard():
    # 1. Open the connection to the Aiven MySQL database
    cursor = open_connection()
    qm = QueryManager(cursor)

    # 2. Fetch all moderation logs
    # This will return a list of dictionaries with keys: id, user_id, action, timestamp, lift_time
    logs = qm.get_all_records()

    # 3. Send the logs to your HTML page
    return render_template('dashboard.html', logs=logs)


@app.route('/unban/<chat_id>/<int:user_id>', methods=['POST'])
def unban_user(chat_id, user_id):
    cursor = open_connection()
    qm = QueryManager(cursor)

    # 1. Tell Telegram Servers to physically unban the user
    telegram_url = f"https://api.telegram.org/bot{keys.API_TOKEN}/unbanChatMember"
    response = requests.get(telegram_url, params={
        "chat_id": chat_id,
        "user_id": user_id,
        "only_if_banned": True
    })

    # 2. If Telegram successfully unbanned them (HTTP 200), update our database
    if response.status_code == 200:
        # We use your team lead's new Soft-Delete function!
        qm.revoke_action(user_id, "Ban")
    else:
        print(f"Failed to unban on Telegram: {response.text}")

    # 3. Refresh the page
    return redirect(url_for('dashboard'))


if __name__ == '__main__':
    app.run(debug=True)
