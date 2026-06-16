import requests
import json
from datetime import datetime
from flask import Flask, render_template, redirect, url_for, request, jsonify, Response, session, flash
import os
import sys
from pathlib import Path

# Fix pathing issues for imports
current_dir = Path(__file__).resolve().parent
src_dir = current_dir.parent
project_root = src_dir.parent
sys.path.append(str(project_root))
sys.path.append(str(src_dir))

from src.DB.Connector import open_connection
from src.DB.QueryManager import QueryManager
from src.Bot.LLM import ask_llm, is_ollama_running
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from env import keys
app = Flask(__name__)
try:
    app.secret_key = keys.SECRET_KEY
except AttributeError:
    app.secret_key = "super-secret-fallback-token-string-change-this-in-production!"


@app.route('/')
def dashboard():
    if not session.get('is_authenticated'):
        return redirect(url_for('login_route'))

    cursor = open_connection()
    qm = QueryManager(cursor)

    GROUP_CHAT_ID = "-1003713767184"
    telegram_url = f"https://api.telegram.org/bot{keys.API_TOKEN}/getChatMemberCount"

    try:
        # Hit the Telegram API
        response = requests.get(telegram_url, params={"chat_id": GROUP_CHAT_ID}, timeout=5)
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

    # 2. Fetch Chart Data
    trend_data_raw = qm.get_moderation_trend()
    growth_data_raw = qm.get_subscriber_growth()

    # Format 7-Day Trend
    trend_labels = [str(row['action_date']) for row in trend_data_raw]
    trend_values = [row['count'] for row in trend_data_raw]

    # Format Subscriber Growth (Cumulative)
    growth_labels = [str(row['sub_date']) for row in growth_data_raw]
    growth_values = []
    current_total = 0
    for row in growth_data_raw:
        current_total += row['count']
        growth_values.append(current_total)

    # Check if Ollama is running in the background
    ai_status = "Online" if is_ollama_running() else "Offline"
    return render_template('dashboard.html',
                           total_users=total_users,
                           total_subs=total_subs,
                           recent_actions=recent_actions,
                           trend_labels=trend_labels,
                           trend_values=trend_values,
                           growth_labels=growth_labels,
                           growth_values=growth_values,
                           ai_status = ai_status)


@app.route('/moderation')
def moderation():
    if not session.get('is_authenticated'):
        return redirect(url_for('login_route'))
    cursor = open_connection()
    qm = QueryManager(cursor)
    # fetch forbidden phrases list
    forbidden_phrases = qm.get_all_forbidden_phrases()

    # count metrics for the pie chart
    cursor.execute("SELECT COUNT(*) as count FROM ModerationActions WHERE action = 'Ban';")
    ban_count = cursor.fetchone()['count'] or 0

    cursor.execute("SELECT COUNT(*) as count FROM ModerationActions WHERE action LIKE 'Mute%';")
    mute_count = cursor.fetchone()['count'] or 0

    # fetch active restrictions
    cursor.execute("SELECT * FROM ModerationActions WHERE lift_time > NOW();")
    active_restrictions = cursor.fetchall()

    # fetch complete history log
    all_logs = qm.get_all_records()

    return render_template('moderation.html',
                           active_restrictions=active_restrictions,
                           all_logs=all_logs,
                           forbidden_phrases=forbidden_phrases,
                           ban_count=ban_count,
                           mute_count=mute_count)


@app.route('/unban/<chat_id>/<int:user_id>', methods=['POST'])
def unban_user(chat_id, user_id):
    cursor = open_connection()
    qm = QueryManager(cursor)

    # track the explicit action rule for removal
    action_to_revoke = request.form.get('action', 'Ban')

    # release call to Telegram core API
    telegram_url = f"https://api.telegram.org/bot{keys.API_TOKEN}/unbanChatMember"
    response = requests.get(telegram_url, params={
        "chat_id": chat_id,
        "user_id": user_id,
        "only_if_banned": True
    })

    # verify target interface update status
    if response.status_code == 200:
        qm.revoke_action(user_id, action_to_revoke)
        flash(f"Successfully lifted {action_to_revoke} for User {user_id}!", "success")
    else:
        flash(f"Telegram API rejected the request to unban User {user_id}.", "danger")
    return redirect(url_for('moderation'))


# --- FORBIDDEN PHRASE MANIPULATION ---
@app.route('/api/forbidden-phrases/add', methods=['POST'])
def add_phrase():
    cursor = open_connection()
    qm = QueryManager(cursor)
    phrase = request.form.get('phrase')
    if phrase:
        qm.add_forbidden_phrase(phrase)
    return redirect(url_for('moderation'))


@app.route('/api/forbidden-phrases/remove', methods=['POST'])
def remove_phrase():
    cursor = open_connection()
    qm = QueryManager(cursor)
    phrase = request.form.get('phrase')
    if phrase:
        qm.remove_forbidden_phrase(phrase)
    return redirect(url_for('moderation'))


# @app.route("/api/slow-mode", methods=["POST"])
# def handle_direct_slow_mode():
#     try:
#         data = request.get_json() or {}
#         chat_id = data.get("chat_id")
#         duration = data.get("duration")
#         if chat_id is None or duration is None:
#             return jsonify({"status": "error", "message": "Missing required fields"}), 400
#         try:
#             duration_int = int(duration)
#             chat_id_int = int(chat_id)
#         except ValueError:
#             return jsonify({"status": "error", "message": "Invalid integer format for chat_id or duration"}), 400
#
#         allowed_durations = [0, 10, 30, 60, 300, 900, 3600]
#         if duration_int not in allowed_durations:
#             return jsonify({"status": "error", "message": "Invalid duration value"}), 400
#
#         url = f"https://api.telegram.org/bot{keys.API_TOKEN}/setChatSlowModeDelay"
#         payload = {
#             "chat_id": chat_id_int,
#             "slow_mode_delay": duration_int
#         }
#
#         response = requests.post(url, json=payload, timeout=10)
#         response_data = response.json()
#         if not response_data.get("ok"):
#             error_msg = response_data.get("description", "Unknown Telegram API error")
#             print(f"!!! TELEGRAM REJECTED IT BECAUSE: {error_msg}")  # Look at your terminal!
#             return jsonify({"status": "error", "message": f"Telegram API error: {error_msg}"}), 400
#
#         message = "Slow mode disabled" if duration_int == 0 else f"Slow mode set to {duration_int}s"
#         return jsonify({"status": "success", "message": message}), 200
#
#     except Exception as e:
#         return jsonify({"status": "error", "message": str(e)}), 500


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

@app.route('/login', methods=['GET', 'POST'])
def login_route():
    if request.method == 'POST':
        user_id = request.form.get('user_id')
        chat_id = request.form.get('chat_id')
        password = request.form.get('password')

        cursor = open_connection()
        qm = QueryManager(cursor)

        if qm.verify_admin_login(user_id, chat_id, password):
            session['is_authenticated'] = True
            session['active_user_id'] = user_id
            session['active_chat_id'] = chat_id
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error="Invalid login parameters supplied.")

    return render_template('login.html', error=None)


@app.route('/logout')
def logout_route():
    session.clear()
    return redirect(url_for('login_route'))


@app.route("/api/ai-draft", methods=["POST"])
def ai_draft():
    data = request.get_json() or {}
    prompt = data.get("prompt")
    mode = data.get("mode", "Formal")

    if not prompt:
        return jsonify({"status": "error", "message": "No prompt provided"}), 400

    # Give the AI specific roles based on the radio button clicked
    if mode == "Casual":
        instructions = "You are a Telegram Messages Rewriter for Administrator of Telegram group chat. Rewrite the following message to be casual and friendly. Keep slang if appropriate, but make slight grammar corrections so it is perfectly understandable. Do not output any thinking process, just the final message.\n\nMessage: "
    elif mode == "Short":
        instructions = "You are a Telegram Messages Rewriter for Administrator of Telegram group chat. Rewrite the following message to be as short and concise as physically possible while still presenting the intended meaning. Do not output any thinking process, just the final message.\n\nMessage: "
    else:  # Formal
        instructions = "You are a Telegram Messages Rewriter for Administrator of Telegram group chat. Rewrite the following message to be highly professional, formal, and grammatically perfect. Do not output any thinking process, just the final message.\n\nMessage: "

    try:
        response_text = ask_llm(instructions + prompt)
        # Clean up the response to remove unwanted quotes the AI might add
        response_text = response_text.strip().strip('"').strip("'")
        return jsonify({"status": "success", "response": response_text}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/export-logs")
def export_logs():
    cursor = open_connection()
    qm = QueryManager(cursor)
    logs = qm.get_all_records()

    # We must convert MySQL datetime objects to strings so they can be downloaded
    clean_logs = []
    for row in logs:
        clean_row = {}
        for key, val in row.items():
            clean_row[key] = str(val) if isinstance(val, datetime) else val
        clean_logs.append(clean_row)

    # Force the browser to download it as a file instead of displaying it
    json_data = json.dumps(clean_logs, indent=4)
    return Response(json_data,
                    mimetype='application/json',
                    headers={'Content-Disposition': 'attachment;filename=moderation_logs.json'})


@app.route('/settings')
def settings():
    # Enforce security: kick out unauthorized guests
    if not session.get('is_authenticated'):
        return redirect(url_for('login_route'))

    # Check background statuses dynamically
    ai_online = is_ollama_running()

    # Check if we can safely talk to our MySQL database
    try:
        cursor = open_connection()
        db_status = "Connected"
    except Exception:
        db_status = "Disconnected"

    return render_template('settings.html',
                           ai_online=ai_online,
                           db_status=db_status,
                           bot_username="@ChatStatsBot")

if __name__ == '__main__':
    app.run(debug=True)
