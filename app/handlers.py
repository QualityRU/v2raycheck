import logging
import os
import random
import re
from collections import defaultdict

import aiofiles
from aiogram import Bot, Router, types
from aiogram.filters import Command
from aiogram.types import (InlineKeyboardButton, InlineKeyboardMarkup,
                           KeyboardButton, ReplyKeyboardMarkup)
from dotenv import load_dotenv

load_dotenv()

CONFIG_CHECK_PATH = os.getenv('CONFIG_CHECK_PATH')

logger = logging.getLogger(__name__)
router = Router()


async def parse_line(line):
    match = re.match(r'^(vmess|vless|trojan|ss)://(.+?)#(.+)$', line)
    if match:
        scheme = match.group(1)
        data = match.group(2)
        country = match.group(3)
        return scheme, data, country
    return None


async def create_dictionary_from_file(filename):
    configs_dict = defaultdict(lambda: defaultdict(list))

    async with aiofiles.open(filename, 'r') as file:
        async for line in file:
            line = line.strip()
            result = await parse_line(line)
            if result:
                scheme, data, country = result
                configs_dict[country][scheme].append(data)

    return configs_dict


country_links_cache = None


async def load_country_links(force_reload=False):
    global country_links_cache
    if country_links_cache is None or force_reload:
        country_links_cache = await create_dictionary_from_file(
            CONFIG_CHECK_PATH
        )
    return country_links_cache


class CallbackData:
    @staticmethod
    def scheme_callback_data(country_name, scheme):
        return f'scheme_{country_name}_{scheme}'

    @staticmethod
    def back_to_country():
        return 'back_to_country'

    @staticmethod
    def refresh_country_list():
        return 'refresh_country_list'


async def delete_message(message: types.Message, bot: Bot):
    try:
        await bot.delete_message(message.chat.id, message.message_id)
    except Exception as e:
        logger.error(f'Failed to delete message: {e}')


async def send_country_keyboard(message: types.Message, bot: Bot):
    country_links = await load_country_links()
    if not country_links:
        await message.answer('Нет доступных стран. Пожалуйста, зайдите позже.')
        return

    sorted_countries = sorted(country_links.keys())
    keyboard_buttons = [
        KeyboardButton(
            text=f'{country} ({sum(len(schemes) for schemes in country_links[country].values())})'
        )
        for country in sorted_countries
    ]
    keyboard_buttons.append(KeyboardButton(text='🔄 Обновить список стран'))
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            keyboard_buttons[i : i + 2]
            for i in range(0, len(keyboard_buttons), 2)
        ],
        resize_keyboard=True,
        one_time_keyboard=True,  # Клавиатура исчезает после выбора
    )

    sent_message = await message.answer(
        'Выберите страну:', reply_markup=keyboard
    )
    await delete_message(message, bot)  # Удаляем старое сообщение


async def send_scheme_keyboard(
    message: types.Message, country_name: str, schemes: dict, bot: Bot
):
    keyboard_buttons = [
        InlineKeyboardButton(
            text=f'{scheme} ({len(schemes[scheme])})',
            callback_data=CallbackData.scheme_callback_data(
                country_name, scheme
            ),
        )
        for scheme in schemes.keys()
    ]

    # Клавиатура с протоколами и кнопкой назад
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[button] for button in keyboard_buttons]
        + [
            [
                InlineKeyboardButton(
                    text='🔙 Назад к выбору страны',
                    callback_data=CallbackData.back_to_country(),
                )
            ]
        ]
    )

    sent_message = await message.answer(
        f'Вы выбрали {country_name}. Теперь выберите протокол:',
        reply_markup=keyboard,
    )
    await delete_message(message, bot)


@router.message(Command('start'))
async def choose_country(message: types.Message, bot: Bot):
    logger.info(
        f'User {message.from_user.id} ({message.from_user.username}) sent command: {message.text}'
    )
    await send_country_keyboard(message, bot)
    await delete_message(message, bot)


@router.message(lambda message: message.text == '🔄 Обновить список стран')
async def refresh_country_list(message: types.Message, bot: Bot):
    logger.info(
        f'User {message.from_user.id} ({message.from_user.username}) sent command: {message.text}'
    )
    await load_country_links(force_reload=True)
    await send_country_keyboard(message, bot)
    await delete_message(message, bot)


@router.message(
    lambda message: message.text
    and message.text not in ['🔄 Обновить список стран']
)
async def process_country_selection(message: types.Message, bot: Bot):
    user_id = message.from_user.id
    username = message.from_user.username
    country_name = message.text.split(' ')[
        0
    ]  # Получаем только название страны без количества

    logger.info(
        f'User {user_id} ({username}) selected country: {country_name}'
    )

    country_links = await load_country_links()

    if country_name in country_links:
        schemes = country_links[country_name]
        await send_scheme_keyboard(message, country_name, schemes, bot)
    else:
        await message.answer(f'Ссылок для {country_name} не найдено.')
        await delete_message(message, bot)  # Удаляем старое сообщение


@router.callback_query(lambda c: c.data and c.data.startswith('scheme_'))
async def process_scheme_callback(
    callback_query: types.CallbackQuery, bot: Bot
):
    user_id = callback_query.from_user.id
    username = callback_query.from_user.username
    _, country_name, scheme = callback_query.data.split('_', 2)

    logger.info(
        f'User {user_id} ({username}) selected scheme: {scheme} for country: {country_name}'
    )

    country_links = await load_country_links()

    if country_links.get(country_name) and country_links[country_name].get(
        scheme
    ):
        data = random.choice(country_links[country_name][scheme])
        await callback_query.answer(
            f'Вот ссылка для {country_name} с протоколом {scheme}:'
        )
        sent_message = await callback_query.message.answer(
            f'{scheme}://{data}'
        )
        await delete_message(callback_query.message, bot)
        logger.info(
            f'Sent link for {country_name} with scheme {scheme} to user {user_id} ({username})'
        )
    else:
        await callback_query.answer(
            f'Ссылок для {country_name} с протоколом {scheme} не найдено.'
        )
        await callback_query.message.answer(
            f'Ссылок для {country_name} с протоколом {scheme} не найдено.'
        )


@router.callback_query(lambda c: c.data == 'back_to_country')
async def back_to_country(callback_query: types.CallbackQuery, bot: Bot):
    logger.info(
        f'User {callback_query.from_user.id} ({callback_query.from_user.username}) requested to go back to country menu.'
    )
    await callback_query.answer()
    await send_country_keyboard(callback_query.message, bot)
    await delete_message(callback_query.message, bot)
