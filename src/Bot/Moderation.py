from datetime import timedelta, datetime
from telegram import Update, ChatPermissions


class Moderation:
    def __init__(self, qm):
        self.query_manager = qm

    async def timeout_user(self, update: Update, user_id, chat_id, context):
        try:
            await context.bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=user_id,
                permissions=ChatPermissions(can_send_messages=False),
                until_date=datetime.utcnow() + timedelta(minutes=5)
            )
            await update.message.reply_text("Muted for 5 minutes due to spamming.")
            return
        except Exception as e:
            print(f"Admin action failed: {e}")


    async def ban_user(self, update: Update, target_user, chat_id, context):
        try:
            await context.bot.ban_chat_member(
                chat_id=chat_id,
                user_id=target_user.id,
                revoke_messages=False
            )
            await update.message.reply_text(
                f"{target_user.first_name} has been banned from the group.")
        except Exception as e:
            print(f"Kick failed: {e}")

    def record_action(self):
        self.query_manager.add_user()
