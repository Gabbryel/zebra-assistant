"""
Handle the basic tasks of the bot
"""

import logging

import telebot
from telebot.apihelper import ApiTelegramException
from telebot.util import extract_arguments

from zebra_assistant import bot, constants, util, func


# handle callback query
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(query):
    try:
        data = query.data
        if data.startswith('verify-captcha-'):
            func.verify_captcha(query)
        elif data.startswith('welcome-') or data.startswith('captcha-') or data.startswith('autopost-'):
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


class IsAuthorized(telebot.custom_filters.SimpleCustomFilter):
    key = 'is_authorized'

    @staticmethod
    def check(message: telebot.types.Message, **kwargs):
        return str(message.from_user.id) in constants.admins_list


bot.add_custom_filter(IsAuthorized())
bot.add_custom_filter(telebot.custom_filters.IsReplyFilter())
