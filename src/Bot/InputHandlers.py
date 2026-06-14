from collections import defaultdict
from datetime import datetime, timedelta
from telegram import Update, ChatPermissions
from telegram.error import Forbidden, TelegramError, BadRequest
from telegram.ext import Application, MessageHandler, filters, ContextTypes

from src.Bot.Connector import open_connection
from src.Bot.Moderation import Moderation
from src.Bot.QueryManager import QueryManager

from src.Bot.LLM import ask_llm, ChatSession
class InputHandlers:
    def __init__(self, app):
        self.user_timestamps = defaultdict(list)
        self.query_manager = QueryManager(open_connection())
        self.moderator = Moderation(self.query_manager, app)
        self.chat_sessions = {}

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        await update.message.reply_html(
            rf"Hi {user.mention_html()}! I'm your new bot. How can I help you today?"
        )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        cmd_list = ["/start - Start the bot",
                    "/help - Show this menu",
                    "/ban - Ban user (you should reply to user's message)",
                    "/ai - Prompt LLM",
                    "/chat - Start/Continue LLM Chat session",
                    ]
        await update.message.reply_text("Available commands:\n"+"\n".join(cmd_list))

    async def ban_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat = update.effective_chat
        issuer_id = update.effective_user.id
        if chat.type not in ["group", "supergroup"]:
            await update.message.reply_text("This command can only be used in group chats.")
            return

        if not update.message.reply_to_message:
            await update.message.reply_text("Please specify target via reply to it's message.")
            return

        target_user = update.message.reply_to_message.from_user
        self.query_manager.log_user(target_user)
        chat_member = await context.bot.get_chat_member(chat_id=chat.id, user_id=issuer_id)
        if chat_member.status not in ["administrator", "creator"]:
            await update.message.reply_text("You do not have permission to use this command.")
            return
        await self.moderator.ban_user(update, target_user, chat.id, context)


    async def show_banned_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        records = self.query_manager.get_banned_users()
        reply = self.query_manager.format_records(records)
        if not reply:
            await update.message.reply_text("No banned users found.")
        await update.message.reply_text(reply)

    async def prompt_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        received_text = " ".join(context.args)
        if received_text:
            instructions="""Be really concise. Answer as professional scientist. Do not use LaTeX syntax. Do not use LaTeX syntax. Do not use LaTeX syntax.\n"""
            await update.message.reply_text("\U0001f916:"+ask_llm(instructions+received_text))
        else:
            await update.message.reply_text("Please provide prompt")

    async def chat_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        received_text = " ".join(context.args)
        if received_text:
            instructions="""Be really concise. Answer as professional scientist. Do not use LaTeX syntax. Do not use LaTeX syntax. Do not use LaTeX syntax.\n"""
            user_id = update.effective_user.id
            if user_id in self.chat_sessions:
                await update.message.reply_text("\U0001f916:"+self.chat_sessions[user_id].ask(received_text))
            else:
                self.chat_sessions[user_id] = ChatSession()
                await update.message.reply_text("\U0001f916:"+self.chat_sessions[user_id].ask(instructions+received_text))
        else:
            await update.message.reply_text("Please provide prompt")

    async def subscribe_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        if update.effective_chat.type == "private":
            await update.message.reply_text(
                "This command must be used inside the group chat you want to subscribe to.")
            return

        success = self.query_manager.subscribe_user(user_id, chat_id)
        if success:

            notification = await update.message.reply_text(
                f"Done! {update.effective_user.first_name}, you've subscribed to notifications from this chat. To ensure your subscription message '/start' to this bot!")
            await update.message.delete()
            context.job_queue.run_once(
                lambda ctx: ctx.bot.delete_message(chat_id=chat_id, message_id=notification.message_id),
                when=10
            )
        else:
            await update.message.reply_text("An error occurred while processing your subscription.")

    async def unsubscribe_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        if update.effective_chat.type == "private":
            await update.message.reply_text("This command must be used inside the group chat.")
            return

        success = self.query_manager.unsubscribe_user(user_id, chat_id)
        if success:
            notification = await update.message.reply_text(f"You have unsubscribed from this group's notifications.")
            await update.message.delete()
            context.job_queue.run_once(
                lambda ctx: ctx.bot.delete_message(chat_id=chat_id, message_id=notification.message_id),
                when=10
            )
        else:
            await update.message.reply_text("An error occurred while processing your request.")

    async def broadcast_news_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.effective_chat or update.effective_chat.type == "private":
            return

        message_text = update.message.text
        if "!News!" in message_text:
            chat_id = update.effective_chat.id
            user_id = update.effective_user.id
            chat_member = await context.bot.get_chat_member(chat_id, user_id)
            if chat_member.status not in ["administrator", "creator"]:
                return

            subscribers = self.query_manager.get_subscribers(chat_id)
            if not subscribers:
                await update.message.reply_text("Broadcasting skipped: There are no subscribers for this chat yet.")
                return

            broadcast_payload = f"**New Announcement from {update.effective_chat.title}:**\n\n{message_text}"
            sent_count = 0
            for sub_id in subscribers:
                try:
                    await context.bot.send_message(chat_id=sub_id, text=broadcast_payload, parse_mode="Markdown")
                    sent_count += 1
                except Forbidden:
                    self.query_manager.unsubscribe_user(sub_id, chat_id)
                except TelegramError:
                    pass

    async def content_filter_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        phrases = self.query_manager.get_all_forbidden_phrases()
        if not update.effective_chat or update.effective_chat.type == "private" or not update.message.text:
            return

        message_text = update.message.text.lower()
        chat_id = update.effective_chat.id
        user = update.effective_user
        try:
            chat_member = await context.bot.get_chat_member(chat_id, user.id)
            if chat_member.status in ["administrator", "creator"]:
                return
        except TelegramError:
            return

        if any(phrase in message_text for phrase in phrases):
            try:
                await update.message.delete()
                await self.moderator.timeout_user(update, user, chat_id, context, 60, "Language")
            except TelegramError as te:
                print(f"Content moderation failed: {te}")


    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        received_text = update.message.text
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        now = datetime.utcnow()

        one_minute_ago = now - timedelta(seconds=60)
        self.user_timestamps[user_id] = [t for t in self.user_timestamps[user_id] if t > one_minute_ago]
        self.user_timestamps[user_id].append(now)

        if len(self.user_timestamps[user_id]) > 10:
            await self.moderator.timeout_user(update, update.effective_user, chat_id, context, 5, "Spamming")
            self.query_manager.log_user(update.effective_user)
            self.user_timestamps[user_id].clear()

        if "hello" in received_text.lower():
            reply_text = "Well, hello there!"
            try:
                await update.message.reply_text(reply_text)
            except Exception as e:
                print(f"Message handler failed: {e}")

    async def toggle_slow_mode(self, chat_id: int, duration: int, context: ContextTypes.DEFAULT_TYPE):
        allowed_durations = [0, 10, 30, 60, 300, 900, 3600]
        if duration not in allowed_durations:
            return False

        try:
            chat_info = await context.bot.get_chat(chat_id)
        except BadRequest:
            return False
        except TelegramError:
            return False

        try:
            current_slow_mode = getattr(chat_info, 'slow_mode_delay', 0) or 0
            if current_slow_mode > 0:
                await context.bot.set_chat_slow_mode_delay(chat_id=chat_id, delay_seconds=0)
            else:
                await context.bot.set_chat_slow_mode_delay(chat_id=chat_id, delay_seconds=duration)
            return True
        except TelegramError:
            return False
