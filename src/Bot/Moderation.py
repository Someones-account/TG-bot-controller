from datetime import timedelta, datetime
from telegram import Update, ChatPermissions


class Moderation:
    def __init__(self, qm, app):
        self.application = app
        self.query_manager = qm
        self.max_timestamp_obj = datetime(2038, 1, 1, 1, 0, 0)

    async def timeout_user(self, update: Update, user, chat_id, context, delta, action):
        try:
            until_date = datetime.now() + timedelta(minutes=5)
            mute_permissions = ChatPermissions(
                can_send_messages=False,
                can_send_audios=False,
                can_send_documents=False,
                can_send_photos=False,
                can_send_videos=False,
                can_send_video_notes=False,
                can_send_voice_notes=False,
                can_send_other_messages=False,
                can_add_web_page_previews=False
            )
            await context.bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=user.id,
                permissions=mute_permissions,
                until_date=until_date
            )
            self.__record_action(user.id, f"Mute {action}", until_date, chat_id)
            notification = await context.bot.send_message(
                chat_id=chat_id,
                text=f"{user.first_name} has been muted for {delta} minutes for using forbidden phrases."
            )
            context.job_queue.run_once(
                lambda ctx: ctx.bot.delete_message(chat_id=chat_id, message_id=notification.message_id),
                when=10
            )
            return
        except Exception as e:
            print(f"Admin action failed: {e}")


    async def ban_user(self, update: Update, target_user, chat_id, context):
        if self.query_manager.is_user_banned(target_user.id, chat_id):
            await update.message.reply_text(
                f"{target_user.first_name} is already banned in this chat."
            )
            return
        try:
            await context.bot.ban_chat_member(
                chat_id=chat_id,
                user_id=target_user.id,
                revoke_messages=False
            )
            self.__record_action(target_user.id, "Ban", self.max_timestamp_obj, chat_id)
            await update.message.reply_text(
                f"{target_user.first_name} has been banned from the group.")
        except Exception as e:
            print(f"Kick failed: {e}")

    async def web_unban_user(self, chat_id: int, user_id: int):
        try:
            await self.application.bot.unban_chat_member(
                chat_id=chat_id,
                user_id=user_id,
                only_if_banned=True
            )
            self.query_manager.revoke_action(user_id, "Ban")
            return True
        except Exception as e:
            print(f"Direct application call failed: {e}")
            return False


    def __record_action(self, user_id, action, lift_time, chat_id):
        try:
            self.query_manager.create_entry(user_id, action, lift_time, chat_id)
        except Exception as e:
            print(f"Failed to record action: {e}")
