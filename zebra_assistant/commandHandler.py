"""
Handle the basic tasks of the bot
"""

import logging

import telebot
from sqlalchemy import insert, select, delete
from telebot.apihelper import ApiTelegramException
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from telebot.util import extract_arguments

from zebra_assistant import bot, constants, util, func, groups, conn


# handle callback query
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(query):
    try:
        data = query.data
        if data.startswith('verify-captcha-'):
            func.verify_captcha(query)
        elif data.startswith('welcome_') or data.startswith('captcha_') or data.startswith('autopost_'):
            func.handle_update_config(query)
        else:
            # bot.answer_callback_query(query.id)
            if data.startswith('config'):
                func.config_commands(query)
    except ApiTelegramException as e:
        if "blocked" in e.result_json['description']:
            pass
        else:
            logging.error(e)
    except Exception as e:
        logging.error(e)


@bot.message_handler(chat_types=['private'], commands=['start'])
def send_welcome(message):
    user_id = extract_arguments(message.text)
    if user_id:
        # TODO: Report User
        pass
    else:
        try:
            bot.send_message(message.chat.id, util.welcome_msg(message.from_user.first_name, message.chat.title))
        except:
            pass


@bot.message_handler(commands=['id'])
def get_id(message):
    try:
        try:
            bot.delete_message(message.chat.id, message.message_id)
        except:
            pass
        bot.send_message(message.chat.id, message.chat.id)
    except:
        pass


@bot.message_handler(content_types=['group_chat_created'])
def chat_created(message):
    try:
        if message.content_type == 'group_chat_created':
            add_group(message.chat.id)
            bot.send_message(message.chat.id, constants.make_me_admin.format(bot_name=constants.name))
            configure_bot_added(message)
    except Exception as e:
        logging.error(e)


@bot.my_chat_member_handler()
def my_chat_handler(message):
    try:
        new = message.new_chat_member
        if new.status == 'left':
            conn.execute(delete(groups).where(groups.c.chat_id == message.chat.id))
        else:
            add_group(message.chat.id)
            configure_bot_added(message)
            if new.status != 'administrator' and message.chat.type == 'group':
                bot.send_message(message.chat.id, constants.make_me_admin.format(bot_name=constants.name))
    except Exception as e:
        logging.error(e)


@bot.message_handler(chat_types=['private'], commands=['config'])
def config_bot(message):
    try:
        bot.delete_message(message.chat.id, message.message_id)
    except:
        pass
    bot.send_message(message.chat.id, "Use /config to configure your bot related settings where bot is added "
                                      "(for Channels you can only do this once, to change configuration "
                                      "remove bot and add again)")


def configure_bot_added(message):
    keyboard = InlineKeyboardMarkup()
    chat_id = message.chat.id
    if message.chat.type == 'channel':
        keyboard.add(InlineKeyboardButton("Subscribe to Contents from Zebra Rec.",
                                          callback_data=f"config_autopost_{chat_id}"))
    else:
        keyboard.add(
            InlineKeyboardButton("Welcome Message", callback_data=f"config_welcome_{chat_id}"),
            InlineKeyboardButton("Captcha Verification", callback_data=f"config_captcha_{chat_id}"),
            InlineKeyboardButton("Subscribe to Contents from Zebra Rec.", callback_data=f"config_autopost_{chat_id}"),
            row_width=1)
    try:
        bot.send_message(message.from_user.id, "You have just Added/Promoted @{bot_username} in the chat"
                                               " {chat_title} Please configure settings"
                                               "\n\nThese are the available options for you"
                         .format(bot_username=constants.username, chat_title=message.chat.title),
                         reply_markup=keyboard)
    except:
        if message.chat.type == 'channel':
            bot.send_message(message.chat.id, "Before adding me Please Initialize me or"
                                              " Unblock if you have blocked me")
            bot.leave_chat(message.chat.id)
        else:
            bot.send_message(message.chat.id, "Use /config to configure your Bot related settings")


@bot.message_handler(content_types=['new_chat_members'])
def new_chat_members_joined(message):
    try:
        for member in message.new_chat_members:
            if not member.is_bot:
                if func.get_welcome(message.chat.id) == "on":
                    bot.send_message(message.chat.id, util.welcome_msg(member.full_name, message.chat.title),
                                     disable_web_page_preview=True)
                if bot.get_chat_member(message.chat.id, message.from_user.id).status not in ['administrator'] \
                        and func.get_captcha(message.chat.id) == "on":
                    try:
                        bot.restrict_chat_member(message.chat.id, member.id)
                        func.solve_captcha(message, member.id)
                    except:
                        pass
    except Exception as e:
        logging.error(e)


def add_group(group_id):
    result = conn.execute(select(groups.c.chat_id).where(groups.c.chat_id == group_id)).fetchone()
    if result is None:
        query = insert(groups).values(chat_id=group_id)
        conn.execute(query)


def handle_cmd(message):
    try:
        if message.text.strip() == '/start':
            send_welcome(message)
        else:
            bot.send_message(message.chat.id, 'Previous Operation Cancelled !! Execute Again')
    except ApiTelegramException as e:
        if "blocked" in e.result_json['description']:
            pass
        else:
            logging.error(e)
    except Exception as e:
        logging.error(e)


bot.add_custom_filter(telebot.custom_filters.IsReplyFilter())
