from datetime import timedelta, datetime
from telegram import Update, ChatPermissions


class Moderation:
    def __init__(self, qm):
        self.query_manager = qm
        self.max_timestamp_obj = datetime(2038, 1, 1, 1, 0, 0)

    async def timeout_user(self, update: Update, user_id, chat_id, context):
        try:
            until_date = datetime.utcnow() + timedelta(minutes=5)
            await context.bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=user_id,
                permissions=ChatPermissions(can_send_messages=False),
                until_date=until_date
            )
            self.__record_action(user_id, "Mute 5min", until_date)
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
            self.__record_action(target_user.id, "Ban", self.max_timestamp_obj)
            await update.message.reply_text(
                f"{target_user.first_name} has been banned from the group.")
        except Exception as e:
            print(f"Kick failed: {e}")

    def __record_action(self, user_id, action, lift_time):
        try:
            self.query_manager.create_entry(user_id, action, lift_time)
        except Exception as e:
            print(f"Failed to record action: {e}")
