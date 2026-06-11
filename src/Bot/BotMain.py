import logging
from telegram.ext import CommandHandler, MessageHandler
from env import keys
from InputHandlers import *

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)
handler = InputHandlers()


def main():
    token = keys.API_TOKEN
    application = Application.builder().token(token).build()
    application.add_handler(CommandHandler("start", handler.start_command))
    application.add_handler(CommandHandler("help", handler.help_command))
    # application.add_handler(CommandHandler("display", handler.console_records))
    application.add_handler(CommandHandler("ban", handler.ban_command))
    application.add_handler(CommandHandler("showbanned", handler.show_banned_command))

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handler.handle_message))
    print("Bot is starting up... Press Ctrl+C to stop.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()