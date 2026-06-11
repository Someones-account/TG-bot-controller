from collections import defaultdict
from datetime import datetime, timedelta
from telegram import Update, ChatPermissions
from telegram.ext import Application, MessageHandler, filters, ContextTypes

from src.Bot.Connector import open_connection
from src.Bot.Moderation import Moderation
from src.Bot.QueryManager import QueryManager


class InputHandlers:
    def __init__(self):
        self.user_timestamps = defaultdict(list)
        self.query_manager = QueryManager(open_connection())
        self.moderator = Moderation(self.query_manager)

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        await update.message.reply_html(
            rf"Hi {user.mention_html()}! I'm your new bot. How can I help you today?"
        )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("Available commands:\n/start - Start the bot\n/help - Show this menu")

    async def ban_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat = update.effective_chat
        issuer_id = update.effective_user.id
        if chat.type not in ["group", "supergroup"]:
            await update.message.reply_text("This command can only be used in group chats.")
            return

        if not update.message.reply_to_message:
            await update.message.reply_text("Please specify target via reply or username to ban them.")
            return

        target_user = update.message.reply_to_message.from_user
        chat_member = await context.bot.get_chat_member(chat_id=chat.id, user_id=issuer_id)
        if chat_member.status not in ["administrator", "creator"]:
            await update.message.reply_text("You do not have permission to use this command.")
            return
        await self.moderator.ban_user(update, target_user, chat.id, context)



    async def console_records(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.query_manager.display_records()
        await update.message.reply_text("Records are displayed in a console!")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        received_text = update.message.text
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        now = datetime.utcnow()

        one_minute_ago = now - timedelta(seconds=60)
        self.user_timestamps[user_id] = [t for t in self.user_timestamps[user_id] if t > one_minute_ago]
        self.user_timestamps[user_id].append(now)

        if len(self.user_timestamps[user_id]) > 10:
            await self.moderator.timeout_user(update, user_id, chat_id, context)
            self.user_timestamps[user_id].clear()

        if "hello" in received_text.lower():
            reply_text = "Well, hello there!"
            try:
                await update.message.reply_text(reply_text)
            except Exception as e:
                print(f"Message handler failed: {e}")