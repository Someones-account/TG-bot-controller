import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from env import keys
from InputHandlers import *

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def main():
    token = keys.API_TOKEN
    application = Application.builder().token(token).build()
    handler = InputHandlers(application)
    application.add_handler(CommandHandler("start", handler.start_command))
    application.add_handler(CommandHandler("help", handler.help_command))
    application.add_handler(CommandHandler("subscribe", handler.subscribe_command))
    application.add_handler(CommandHandler("unsubscribe", handler.unsubscribe_command))
    application.add_handler(CommandHandler("ban", handler.ban_command))
    application.add_handler(CommandHandler("showbanned", handler.show_banned_command))
    application.add_handler(CommandHandler("password", handler.get_password_command))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handler.content_filter_handler),
        group=0
    )
    application.add_handler(CommandHandler("ai", handler.prompt_command))
    application.add_handler(CommandHandler("chat", handler.chat_command))
    
    application.add_handler(CommandHandler("context_chat", handler.context_chat_command))

    application.add_handler(CommandHandler("vision", handler.vision_command))
    application.add_handler(MessageHandler(filters.PHOTO, handler.vision_command), group=3)

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handler.broadcast_news_handler),group=2)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handler.handle_message),group=1)
    print("Bot is starting up... Press Ctrl+C to stop.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
