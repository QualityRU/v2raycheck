import logging
import os
from asyncio import run

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from colorama import Fore, Style, init
from dotenv import load_dotenv

from app.handlers import router

load_dotenv()  # Load environment variables from .env file

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Initialize colorama
init(autoreset=True)


class ColoredFormatter(logging.Formatter):
    def format(self, record):
        if record.levelno == logging.DEBUG:
            color = Fore.CYAN
        elif record.levelno == logging.INFO:
            color = Fore.GREEN
        elif record.levelno == logging.WARNING:
            color = Fore.YELLOW
        elif record.levelno == logging.ERROR:
            color = Fore.RED
        elif record.levelno == logging.CRITICAL:
            color = Fore.MAGENTA
        else:
            color = Fore.WHITE
        return color + super().format(record) + Style.RESET_ALL


# Configure logging
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setFormatter(
    ColoredFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
)
logger.addHandler(handler)
logger.setLevel(logging.INFO)


async def main() -> None:
    logger.info('Starting bot')

    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    dp.include_router(router)

    await dp.start_polling(bot)


if __name__ == '__main__':
    try:
        run(main())
    except KeyboardInterrupt:
        logger.info('Bot stopped by user')
