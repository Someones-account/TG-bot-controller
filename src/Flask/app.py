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


@app.route('/unban/<int:log_id>', methods=['POST'])
def unban_user(log_id):
    # Open DB and delete the record
    cursor = open_connection()
    qm = QueryManager(cursor)
    qm.delete_entry(log_id)

    # Refresh the page automatically so the user disappears from the table
    return redirect(url_for('dashboard'))


if __name__ == '__main__':
    app.run(debug=True)
