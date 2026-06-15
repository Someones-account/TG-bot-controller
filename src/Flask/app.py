import requests
from flask import Flask, render_template, redirect, url_for, request, jsonify
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

from src.DB.Connector import open_connection
from src.Bot.QueryManager import QueryManager
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from env import keys
app = Flask(__name__)


@app.route('/')
def dashboard():
    cursor = open_connection()
    qm = QueryManager(cursor)

    GROUP_CHAT_ID = "-1003713767184"
    telegram_url = f"https://api.telegram.org/bot{keys.API_TOKEN}/getChatMemberCount"

    try:
        # Hit the Telegram API
        response = requests.get(telegram_url, params={"chat_id": GROUP_CHAT_ID})
        data = response.json()

        # If Telegram responds successfully, use their real number
        if data.get("ok"):
            total_users = data.get("result")
        else:
            # Fallback to database if Telegram gets mad
            total_users = qm.get_total_users()
    except Exception as e:
        print(f"Failed to fetch from Telegram API: {e}")
        total_users = qm.get_total_users()

    # 1. Fetch our three summary metrics
    total_subs = qm.get_total_subscribers()
    recent_actions = qm.get_recent_actions_count()

    return render_template('dashboard.html',
                           total_users=total_users,
                           total_subs=total_subs,
                           recent_actions=recent_actions)


@app.route('/moderation')
def moderation():
    cursor = open_connection()
    qm = QueryManager(cursor)

    # fetch active bans
    active_bans = qm.get_banned_users()
    # fetch moderation history
    all_logs = qm.get_all_records()
    return render_template('moderation.html', active_bans=active_bans, all_logs=all_logs)


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


@app.route("/api/slow-mode", methods=["POST"])
def handle_direct_slow_mode():
    try:
        data = request.get_json() or {}
        chat_id = data.get("chat_id")
        duration = data.get("duration")
        if chat_id is None or duration is None:
            return jsonify({"status": "error", "message": "Missing required fields"}), 400
        try:
            duration_int = int(duration)
            chat_id_int = int(chat_id)
        except ValueError:
            return jsonify({"status": "error", "message": "Invalid integer format for chat_id or duration"}), 400

        allowed_durations = [0, 10, 30, 60, 300, 900, 3600]
        if duration_int not in allowed_durations:
            return jsonify({"status": "error", "message": "Invalid duration value"}), 400

        url = f"https://api.telegram.org/bot{keys.API_TOKEN}/setChatSlowModeDelay"
        payload = {
            "chat_id": chat_id_int,
            "delay_seconds": duration_int
        }

        response = requests.post(url, json=payload, timeout=10)
        response_data = response.json()
        if not response_data.get("ok"):
            error_msg = response_data.get("description", "Unknown Telegram API error")
            return jsonify({"status": "error", "message": f"Telegram API error: {error_msg}"}), 400

        message = "Slow mode disabled" if duration_int == 0 else f"Slow mode set to {duration_int}s"
        return jsonify({"status": "success", "message": message}), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/broadcast', methods=['POST'])
def send_broadcast():
    cursor = open_connection()
    qm = QueryManager(cursor)

    # 1. Get the data from our web form
    message_text = request.form.get('message')
    image_url = request.form.get('image_url')

    # In HTML forms, checkboxes send 'on' if checked, and None if unchecked
    send_to_subs = request.form.get('send_subs') == 'on'
    send_to_group = request.form.get('send_group') == 'on'

    GROUP_CHAT_ID = "-1003713767184"
    formatted_message = f"**📣 Admin Announcement:**\n\n{message_text}"

    # 2. Helper function to send the message to a specific ID
    def send_telegram_msg(target_id):
        if image_url:
            # Send as an image with text attached as a caption
            url = f"https://api.telegram.org/bot{keys.API_TOKEN}/sendPhoto"
            payload = {"chat_id": target_id, "photo": image_url, "caption": formatted_message, "parse_mode": "Markdown"}
        else:
            # Send as standard text
            url = f"https://api.telegram.org/bot{keys.API_TOKEN}/sendMessage"
            payload = {"chat_id": target_id, "text": formatted_message, "parse_mode": "Markdown"}

        requests.post(url, json=payload)

    # 3. Execute based on checkboxes!
    if send_to_group:
        send_telegram_msg(GROUP_CHAT_ID)

    if send_to_subs:
        subs = qm.get_subscribers(GROUP_CHAT_ID)
        for sub_id in subs:
            send_telegram_msg(sub_id)

    # 4. Refresh the dashboard page instantly
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    app.run(debug=True)
