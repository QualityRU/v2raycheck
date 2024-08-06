import logging
import random
from collections import defaultdict

from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

router = Router()


def load_country_links():
    country_links = defaultdict(list)
    try:
        with open('configs.txt', 'r') as file:
            for line in file:
                line = line.strip()
                if line:
                    try:
                        url, country = line.rsplit('#', 1)
                        country_links[country].append(url)
                    except ValueError:
                        logger.error(f'Error parsing line: {line}')
    except FileNotFoundError:
        logger.error('configs.txt file not found.')
    return country_links


class CountryCallbackData:
    @staticmethod
    def country_callback_data(country_name):
        return f'country_{country_name}'


@router.message(Command('start'))
@router.message(Command('help'))
async def send_welcome(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username
    command = message.text
    logger.info(f'User {user_id} ({username}) sent command: {command}')
    await message.reply(
        'Hello! Use /choose to select a country and get a link.'
    )


@router.message(Command('choose'))
async def choose_country(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username
    command = message.text
    logger.info(f'User {user_id} ({username}) sent command: {command}')

    country_links = load_country_links()
    if not country_links:
        await message.reply('No countries available. Please check back later.')
        return

    keyboard_buttons = [
        InlineKeyboardButton(
            text=country,
            callback_data=CountryCallbackData.country_callback_data(country),
        )
        for country in country_links.keys()
    ]
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            keyboard_buttons[i : i + 2]
            for i in range(0, len(keyboard_buttons), 2)
        ]
    )

    await message.reply('Select a country:', reply_markup=keyboard)


@router.callback_query(lambda c: c.data and c.data.startswith('country_'))
async def process_callback(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    username = callback_query.from_user.username
    country_name = callback_query.data[len('country_') :]

    logger.info(
        f'User {user_id} ({username}) selected country: {country_name}'
    )

    country_links = load_country_links()

    if country_links.get(country_name):
        random_link = random.choice(country_links[country_name])
        await callback_query.answer(f'Here is a link for {country_name}:')
        await callback_query.message.answer(random_link)
        logger.info(
            f'Sent link for {country_name} to user {user_id} ({username})'
        )
    else:
        await callback_query.answer(f'No links found for {country_name}.')
        await callback_query.message.answer(
            f'No links found for {country_name}.'
        )
        logger.warning(
            f'No links found for {country_name} for user {user_id} ({username})'
        )
