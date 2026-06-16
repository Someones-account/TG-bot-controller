from collections import defaultdict
from datetime import datetime, timedelta
from telegram import Update
from telegram.error import Forbidden, TelegramError
from telegram.ext import ContextTypes

from src.DB.Connector import open_connection
from src.Bot.Moderation import Moderation
from src.DB.QueryManager import QueryManager

from src.Bot.LLM import *
from config import ai

import tempfile
import os
import asyncio
import re

ContextChat = ContextChat()


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
        cmd_list = [
            "/start - Start the bot",
            "/help - Show this menu",
            "/ban - Ban user (you should reply to user's message)",
            "/unmute - Unmute user (you should reply to user's message)",
            "/subscribe - Agree to receive news in your private messages",
            "/unsubscribe - Remove your subscription",
            "/ai - Prompt LLM",
            "/chat - Start/Continue LLM Chat session",
            "/context_chat - Prompt LLM with context (It remembers chat history)",
            "/vision - Prompt LLM about the image. By default(without any parameters provided, just writes text from image)",
        ]
        await update.message.reply_text("Available commands:\n" + "\n".join(cmd_list))

    async def ban_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat = update.effective_chat
        issuer_id = update.effective_user.id
        if chat.type not in ["group", "supergroup"]:
            await update.message.reply_text(
                "This command can only be used in group chats."
            )
            return

        if not update.message.reply_to_message:
            await update.message.reply_text(
                "Please specify target via reply to it's message."
            )
            return

        target_user = update.message.reply_to_message.from_user
        self.query_manager.log_user(target_user)
        chat_member = await context.bot.get_chat_member(
            chat_id=chat.id, user_id=issuer_id
        )
        if chat_member.status not in ["administrator", "creator"]:
            await update.message.reply_text(
                "You do not have permission to use this command."
            )
            return
        await self.moderator.ban_user(update, target_user, chat.id, context)

    async def show_banned_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        records = self.query_manager.get_banned_users()
        reply = self.query_manager.format_records(records)
        if not reply:
            await update.message.reply_text("No banned users found.")
        await update.message.reply_text(reply)

    async def prompt_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        received_text = " ".join(context.args)
        if received_text:
            instructions = """Be really concise. Answer as professional scientist. Do not use LaTeX syntax. Do not use LaTeX syntax. Do not use LaTeX syntax.\n"""
            await update.message.reply_text(
                "\U0001f916:" + ask_llm(instructions + received_text)
            )
        else:
            await update.message.reply_text("Please provide prompt")

    async def chat_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        received_text = " ".join(context.args)
        if received_text:
            instructions = """Be really concise. Answer as professional scientist. Do not use LaTeX syntax. Do not use LaTeX syntax. Do not use LaTeX syntax.\n"""
            user_id = update.effective_user.id
            if user_id in self.chat_sessions:
                await update.message.reply_text(
                    "\U0001f916:" + self.chat_sessions[user_id].ask(received_text)
                )
            else:
                self.chat_sessions[user_id] = ChatSession()
                await update.message.reply_text(
                    "\U0001f916:"
                    + self.chat_sessions[user_id].ask(instructions + received_text)
                )
        else:
            await update.message.reply_text("Please provide prompt")

    async def context_chat_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        received_text = " ".join(context.args)
        if received_text:
            await update.message.reply_text(
                "\U0001f4dd:" + ContextChat.ask(received_text)
            )
        else:
            await update.message.reply_text("Please provide prompt")

    async def subscribe_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        if update.effective_chat.type == "private":
            await update.message.reply_text(
                "This command must be used inside the group chat you want to subscribe to."
            )
            return

        success = self.query_manager.subscribe_user(user_id, chat_id)
        if success:

            notification = await update.message.reply_text(
                f"Done! {update.effective_user.first_name}, you've subscribed to notifications from this chat. To ensure your subscription message '/start' to this bot!"
            )
            await update.message.delete()
            context.job_queue.run_once(
                lambda ctx: ctx.bot.delete_message(
                    chat_id=chat_id, message_id=notification.message_id
                ),
                when=10,
            )
        else:
            await update.message.reply_text(
                "An error occurred while processing your subscription."
            )

    async def unsubscribe_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        if update.effective_chat.type == "private":
            await update.message.reply_text(
                "This command must be used inside the group chat."
            )
            return

        success = self.query_manager.unsubscribe_user(user_id, chat_id)
        if success:
            notification = await update.message.reply_text(
                f"You have unsubscribed from this group's notifications."
            )
            await update.message.delete()
            context.job_queue.run_once(
                lambda ctx: ctx.bot.delete_message(
                    chat_id=chat_id, message_id=notification.message_id
                ),
                when=10,
            )
        else:
            await update.message.reply_text(
                "An error occurred while processing your request."
            )

    async def get_password_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        if update.effective_chat.type != "private":
            await update.message.reply_text(
                "For security reasons, this command can only be used in a private message with me."
            )
            return

        if not context.args:
            await update.message.reply_text(
                "💡 Usage: Send `/password <group_chat_id>` to generate a dashboard token.",
                parse_mode="Markdown",
            )
            return

        try:
            target_chat_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text(
                "Invalid Group ID format. Please check the numerical argument."
            )
            return

        user_id = update.effective_user.id
        username = update.effective_user.username or update.effective_user.first_name
        try:
            member_status = await context.bot.get_chat_member(
                chat_id=target_chat_id, user_id=user_id
            )
            if member_status.status not in ["administrator", "creator"]:
                await update.message.reply_text(
                    "Access Denied: You are not registered as an administrator in that group."
                )
                return

            pwd = self.query_manager.generate_or_get_chat_password(
                user_id, target_chat_id, username
            )

            target_chat = await context.bot.get_chat(target_chat_id)
            response_msg = (
                f"**Dashboard Key Assigned**\n\n"
                f"**Group:** {target_chat.title}\n"
                f"**Your User ID:** `{user_id}`\n"
                f"**Web Password:** `{pwd}`\n\n"
                f"Keep this password confidential. Use these details to log into your control panel."
            )
            await update.message.reply_text(response_msg, parse_mode="Markdown")

        except TelegramError as e:
            print(f"Telegram Admin Validation failed: {e}")
            await update.message.reply_text(
                "Verification Failed: I cannot verify your status. Am I an admin in that group?"
            )

    async def broadcast_news_handler(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
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
                await update.message.reply_text(
                    "Broadcasting skipped: There are no subscribers for this chat yet."
                )
                return

            broadcast_payload = f"**New Announcement from {update.effective_chat.title}:**\n\n{message_text}"
            sent_count = 0
            for sub_id in subscribers:
                try:
                    await context.bot.send_message(
                        chat_id=sub_id, text=broadcast_payload, parse_mode="Markdown"
                    )
                    sent_count += 1
                except Forbidden:
                    self.query_manager.unsubscribe_user(sub_id, chat_id)
                except TelegramError:
                    pass

    async def content_filter_handler(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        phrases = self.query_manager.get_all_forbidden_phrases()
        if (
            not update.effective_chat
            or update.effective_chat.type == "private"
            or not update.message.text
        ):
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
                await self.moderator.timeout_user(
                    update, user, chat_id, context, 60, "Language"
                )
            except TelegramError as te:
                print(f"Content moderation failed: {te}")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        received_text = update.message.text
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        now = datetime.utcnow()

        one_minute_ago = now - timedelta(seconds=60)
        self.user_timestamps[user_id] = [
            t for t in self.user_timestamps[user_id] if t > one_minute_ago
        ]
        self.user_timestamps[user_id].append(now)

        if len(self.user_timestamps[user_id]) > 10:
            await self.moderator.timeout_user(
                update, update.effective_user, chat_id, context, 5, "Spamming"
            )
            self.query_manager.log_user(update.effective_user)
            self.user_timestamps[user_id].clear()

        if "hello" in received_text.lower():
            reply_text = "Well, hello there!"
            try:
                await update.message.reply_text(reply_text)
            except Exception as e:
                print(f"Message handler failed: {e}")

        if ai.MODERATION:
            result = ask_llm(
                ai.MODERATION_INSTRUCTION + "\n MESSAGE:\n" + received_text.lower()
            )
            if result.lower() == "yes":
                await update.message.reply_text("UNPLEASANT CONTENT DETECTED")

        ContextChat.record(user_id, received_text)

    async def vision_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        IMAGE_NOT_FOUND_MESSAGE = (
            "Please attach an image, or reply to an image with /vision."
        )
        WAITING_MESSAGE = "Waiting for a vision model answer..."
        FAIL_MESSAGE = "Vision failed: "
        PROMPT_INSTRUCTION = "If not told otherwise. Be concise.\n"
        DEFAULT_PROMPT = "Write all the text in the image. Don't comment it, only write the content of the image."

        message = update.effective_message
        if not message:
            return

        photo_sizes = None
        if message.photo:
            photo_sizes = message.photo
        elif message.reply_to_message and message.reply_to_message.photo:
            photo_sizes = message.reply_to_message.photo

        if not photo_sizes:
            await message.reply_text(IMAGE_NOT_FOUND_MESSAGE)
            return

        # await message.reply_text("Vision command received.")

        photo = photo_sizes[-1]
        tg_file = await photo.get_file()

        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                tmp_path = tmp.name

            await tg_file.download_to_drive(custom_path=tmp_path)

            instructions = ""
            prompt = " ".join(context.args).strip() if context.args else ""
            if not prompt:
                raw_text = message.caption or ""
                prompt = re.sub(r"^/vision(@\w+)?\s*", "", raw_text).strip()

            if not prompt:
                prompt = DEFAULT_PROMPT
            else:
                instructions = PROMPT_INSTRUCTION

            await message.reply_text(WAITING_MESSAGE)

            answer = await asyncio.to_thread(
                ask_vision_model,
                instructions + prompt,
                [tmp_path],
            )

            await message.reply_text(answer)

        except Exception as e:
            await message.reply_text(f"{FAIL_MESSAGE}{e}")
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)
