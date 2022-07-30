"""
Functions for getting data from different sources
"""
import logging
import random

import schedule
from captcha.image import ImageCaptcha
from fp.fp import FreeProxy
from sqlalchemy import update, delete, select, text
from telebot.apihelper import ApiTelegramException
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from zebra_assistant import constants, bot, conn, groups

USER_AGENTS = [
    "Mozilla/5.0 (Windows; U; Windows NT 6.3) AppleWebKit/538.2.1 (KHTML, like Gecko) Chrome/25.0.867.0 Safari/538.2.1",
    "Mozilla/5.0 (compatible; MSIE 10.0; Windows NT 6.2; Trident/7.0; .NET CLR 1.9.44278.3)",
    "Mozilla/5.0 (Windows; U; Windows NT 6.2) AppleWebKit/536.2.1 (KHTML, like Gecko) Chrome/25.0.868.0 Safari/536.2.1",
    "Mozilla/5.0 (compatible; MSIE 8.0; Windows NT 5.0; Trident/7.0; .NET CLR 4.8.76307.3)",
    "Mozilla/5.0 (Windows; U; Windows NT 5.2) AppleWebKit/535.0.1 (KHTML, like Gecko) Chrome/34.0.862.0 Safari/535.0.1",
    "Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.2; Trident/5.1; .NET CLR 2.6.78583.0)",
    "Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_5_1 rv:4.0; LV) AppleWebKit/534.0.1 (KHTML, like Gecko) "
    "Version/7.1.2 Safari/534.0.1",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.10.1; rv:9.5) Gecko/20100101 Firefox/9.5.2",
    "Mozilla/5.0 (Windows; U; Windows NT 6.0) AppleWebKit/537.2.0 (KHTML, like Gecko) Chrome/34.0.813.0 Safari/537.2.0",
    "Mozilla/5.0 (Windows; U; Windows NT 6.1) AppleWebKit/536.0.0 (KHTML, like Gecko) Chrome/18.0.868.0 Safari/536.0.0"]


def get_proxy():
    try:
        proxy = FreeProxy().get()
        if proxy:
            return proxy
        raise Exception("No proxy found")
    except:
        return None


def antiflood(function, *args, **kwargs):
    """
    Use this function inside loops in order to avoid getting TooManyRequests error.
    :param function:
    :param args:
    :param kwargs:
    :return: None
    """
    from telebot.apihelper import ApiTelegramException
    from time import sleep
    msg = None
    try:
        msg = function(*args, **kwargs)
    except ApiTelegramException as ex:
        if ex.error_code == 429:
            sleep(ex.result_json['parameters']['retry_after'])
            msg = function(*args, **kwargs)
    finally:
        return msg


def joined_channel(member_id):
    """
    :param member_id: user id
    :return: True if user is a member of the channel, False otherwise
    and if user hasn't joined the channel prompt him to join
    """
    try:
        if check_user("@" + constants.bot_owner, member_id):
            return True
        else:
            keyboard = InlineKeyboardMarkup()
            keyboard.add(InlineKeyboardButton('Join', url=f"t.me/{constants.bot_owner}"))
            bot.send_message(member_id, f"To use this special feature of bot you have to join @{constants.bot_owner}\n"
                                        "It will be easier for you to find me in future if I got blocked by telegram.",
                             reply_markup=keyboard)
            return False
    except:
        return True


def check_user(chat_id, member_id):
    """
    :param chat_id: chat id
    :param member_id: user id
    :return: True if user is a member of the chat, False otherwise
    """
    try:
        response = bot.get_chat_member(chat_id, member_id)
        return not (response.status == 'kicked' or response.status == 'left')
    except:
        return False


def sender_name(message):
    """
    :param message: Message object
    :return: name of forwarder
    """
    username = '@' + str(message.from_user.username) if message.from_user.username else message.from_user.first_name
    sender = f'{username} ' if username else 'User '
    return f'{sender} ({message.from_user.id}) '


def edit_report(message, msg_txt):
    """
    :param message: Message object
    :param msg_txt: text of message
    Modify message text in report format
    """
    if msg_txt:
        return f'<b>{sender_name(message)} :- </b>' + msg_txt
    return ''


welcome_preferences = {}
captcha_preferences = {}


def update_chat_id(error, chat_id):
    try:
        old_chat_id = int(chat_id)
        new_chat_id = int(error.result_json.get('parameters').get('migrate_to_chat_id'))
        query = update(groups).values(chat_id=new_chat_id).where(groups.c.chat_id == old_chat_id)
        conn.execute(query)
        return new_chat_id
    except:
        return None


def get_chat_id(chat_id):
    try:
        if chat_id[0] == "-" and chat_id[1:4] != "100":
            bot.delete_message(chat_id, bot.send_message(chat_id, "Test Message").message_id)
        return int(chat_id)
    except ApiTelegramException as e:
        error = e.result_json['description']
        if "upgraded to a supergroup" in error.lower():
            return update_chat_id(error, chat_id)
        elif "kicked from the group chat" in error.lower():
            query = delete(groups).where(groups.c.chat_id == chat_id)
            conn.execute(query)
        return chat_id
    except Exception as e:
        logging.error(e)


def get_group_configuration():
    try:
        welcome_preferences.clear()
        captcha_preferences.clear()
        query = select(groups.c.chat_id, groups.c.welcome, groups.c.captcha)
        result = conn.execute(query).fetchall()
        updated_ids = {}
        for user in result:
            old_id = user[0]
            chat_id = get_chat_id(chat_id=str(old_id))  # may or may not be changed
            try:
                welcome = user[1]
            except:
                welcome = 'on'
            try:
                captcha = user[2]
            except:
                captcha = 'on'
            welcome_preferences[chat_id] = welcome
            captcha_preferences[chat_id] = captcha
            if chat_id != old_id:
                updated_ids[old_id] = chat_id
        return updated_ids
    except Exception as e:
        logging.error(e)


def get_new_uid(old_uid):
    updated_uids = get_group_configuration()
    return updated_uids.get(old_uid)


def get_welcome(uid):
    try:
        result = welcome_preferences.get(uid)
        if result is None:
            result = welcome_preferences.get(get_new_uid(old_uid=uid))
            return result if result else 'on'
        else:
            return result
    except Exception as e:
        logging.error(e)


def get_captcha(uid):
    try:
        result = captcha_preferences.get(uid)
        if result is None:
            result = captcha_preferences.get(get_new_uid(old_uid=uid))
            return result if result else 'on'
        else:
            return result
    except Exception as e:
        logging.error(e)


def generate_captcha(n):
    # Characters to be included
    chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    captcha = ""
    while n:
        captcha += chars[random.randint(1, 1000) % 62]
        n -= 1
    return captcha


def solve_captcha(message, member_id):
    try:
        correct_response = generate_captcha(5)
        options = [generate_captcha(5), correct_response, generate_captcha(5)]
        random.shuffle(options)

        markup_options = list(map(
            lambda x: InlineKeyboardButton(f'{x}',
                                           callback_data=f'verify-captcha-{x}-{correct_response}-{member_id}'),
            options))

        keyboard = InlineKeyboardMarkup()
        keyboard.keyboard.append(markup_options)

        image = ImageCaptcha(width=280, height=90)
        bot.send_photo(message.chat.id, image.generate(correct_response),
                       caption="Solve this Captcha to Verify your Identity.", reply_markup=keyboard)
    except Exception as e:
        logging.error(e)


def verify_captcha(query):
    message = query.message
    try:
        user_response, correct_response, member_id = query.data[15:].split("-")

        if query.from_user.id != int(member_id):
            bot.answer_callback_query(query.id, "Only Unverified New User can solve!", show_alert=True)
            return
        if user_response == correct_response:
            bot.delete_message(message.chat.id, message.message_id)
            bot.restrict_chat_member(message.chat.id, query.from_user.id, None, True, True, True, True, True, True,
                                     True, True)
        else:
            bot.answer_callback_query(query.id, "Verification Failed!", show_alert=True)
    except:
        if bot.get_chat_member(message.chat.id, bot.get_me().id).status not in ['administrator', 'creator']:
            bot.send_message(message.chat.id,
                             "Please make me an admin with all rights and permissions in order for me to complete "
                             "this request !!")
        else:
            pass


def addBroadcast(title, url, time, chats):
    try:
        schedule.every(time).seconds.do(sendBroadcast, title=title, url=url, chats=chats)
    except Exception as e:
        logging.error(e)


def sendBroadcast(title, url, chats):
    try:
        msg = "<b>Video is Live Now Check it out !!</b>\n<a href='{}'>{}</a>".format(url, title)
        keyboard = InlineKeyboardMarkup(row_width=1)
        keyboard.add(InlineKeyboardButton(text="Watch on Youtube", url=url))
        for chat in chats:
            try:
                msg = bot.send_message(chat, msg, reply_markup=keyboard, parse_mode="HTML",
                                       disable_web_page_preview=False)
            except ApiTelegramException:
                pass
        return schedule.CancelJob
    except Exception as e:
        logging.error(e)


def config_commands(query):
    message = query.message
    data = query.data
    chat_id = data.split('_')[2]
    try:
        if bot.get_chat_member(chat_id, query.from_user.id).status not in ['administrator', 'creator']:
            bot.answer_callback_query(query.id, "Only Admins can Configure group settings!", show_alert=True)
            return
        arg = data.split("_")[1]
        bot.delete_message(message.chat.id, message.message_id)
        if arg == "welcome" or arg == "captcha" or arg == "autopost":
            if arg == "welcome":
                msg = "Welcome Message"
            elif arg == "captcha":
                msg = "Captcha Verification"
            else:
                msg = "Auto Post"
            keyboard = InlineKeyboardMarkup()
            query = text(f"SELECT {arg} FROM groups_config where chat_id = {chat_id}")
            result = conn.execute(query).fetchone()
            if result[0] == 'off':
                keyboard.row(InlineKeyboardButton(f'Turn {msg} On', callback_data=f'{arg}_on_{chat_id}'))
            else:
                keyboard.row(InlineKeyboardButton(f'Turn {msg} Off', callback_data=f'{arg}_off_{chat_id}'))
            chat = bot.get_chat(chat_id)
            if arg == "welcome" or arg == "captcha":
                bot.send_message(message.chat.id, f"This will Enable/disable {msg} for New Users in {chat.title}",
                                 reply_markup=keyboard)
            else:
                bot.send_message(message.chat.id, f"This will Enable/disable {msg} in {chat.title}",
                                 reply_markup=keyboard)
    except Exception as e:
        logging.error(e)


def handle_update_config(query):
    message = query.message
    arg, option, chat_id = query.data.split("_")
    try:
        if bot.get_chat_member(chat_id, query.from_user.id).status not in ['administrator', 'creator']:
            bot.answer_callback_query(query.id, "Only Admins can Configure group settings!", show_alert=True)
            return
        sql_query = text(f"UPDATE groups_config SET {arg} = '{option}' WHERE chat_id = {chat_id}")
        conn.execute(sql_query)
        if arg == "welcome":
            welcome_preferences[chat_id] = option
        else:
            captcha_preferences[chat_id] = option
        keyboard = InlineKeyboardMarkup()
        if arg == "welcome":
            msg = "Welcome Message"
        elif arg == "captcha":
            msg = "Captcha Verification"
        else:
            msg = "Auto Post"
        if option == 'off':
            keyboard.row(InlineKeyboardButton(f'Turn {msg} On', callback_data=f'{arg}_on_{chat_id}'))
        else:
            keyboard.row(InlineKeyboardButton(f'Turn {msg} Off', callback_data=f'{arg}_off_{chat_id}'))
        bot.answer_callback_query(query.id, "Configurations Updated Successfully!")
        bot.edit_message_reply_markup(message.chat.id, message.message_id, reply_markup=keyboard)
    except Exception as e:
        logging.error(e)


def handle_cmd(message):
    try:
        if message.text[0] == '/':
            bot.send_message(message.chat.id, "Unrecognized command.")
        else:
            bot.send_message(message.chat.id, "Use Commands only.")
    except Exception as e:
        logging.error(e)
