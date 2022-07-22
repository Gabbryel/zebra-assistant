"""
Group command handlers
"""
import json
import logging
import string
import threading
import time
from datetime import datetime

import schedule
import telebot
from sqlalchemy import update, select
from telebot.apihelper import ApiTelegramException
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from zebra_assistant import bot, func, repository, constants, groups, posts, conn

MAKE_ME_ADMIN = "Please make me an admin with all rights and permissions in order for me to complete this request !!"


def check_for_new_updates(id_chat):
    try:
        check_msg = bot.send_message(id_chat, "Checking for new updates...", disable_notification=True)
        query = select(groups.c.chat_id).where(groups.c.autopost == 'on')
        result = conn.execute(query).fetchall()
        result = [group[0] for group in result]
        yt_response = send_yt_videos(result)
        bc_featured = send_featured_bandcamp_album(result)
        insta_response = send_insta_post(result)
        fb_response = send_facebook_posts(result)
        zb_response = send_zebrabooking_dj(result)
        if yt_response or bc_featured or insta_response or fb_response or zb_response:
            bot.delete_message(id_chat, check_msg.message_id)
        else:
            bot.edit_message_text("<b>Checked</b> No new Video/Post/Track found.", id_chat,
                                  check_msg.message_id)
    except ApiTelegramException as e:
        logging.error(e.result_json)
    except Exception as e:
        logging.error(e)


@bot.message_handler(is_admin=True, chat_types=['group', 'supergroup'], commands=['check'])
def check_posts(message):
    try:
        try:
            bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
        except:
            pass
        threading.Thread(target=check_for_new_updates, args=(message.chat.id,)).start()
    except Exception as e:
        logging.error(e)


def send_yt_videos(chats):
    try:
        query = select(posts.c.last_yt_video_sent)
        response = conn.execute(query).fetchone()
        videos = repository.get_yt_videos(constants.yt_api_key, constants.yt_channel_id, response[0])
        if isinstance(videos, Exception):
            # logging.error(videos)
            return False
        else:
            for video in videos:
                upcoming = True if video.get("liveBroadcastContent") == "upcoming" else False
                keyboard = InlineKeyboardMarkup(row_width=1)
                keyboard.add(InlineKeyboardButton(text="Watch on Youtube", url=video.get("url")))
                msg = "<b>New Youtube Video</b>\n<a href='{}'>{}</a>".format(video.get('url'), video.get('title'))
                for chat in chats:
                    try:
                        msg = bot.send_message(chat, msg, reply_markup=keyboard, parse_mode="HTML",
                                               disable_web_page_preview=False)
                    except ApiTelegramException:
                        pass
                    for entity in msg.entities:
                        if entity.url == 'text_url':
                            logging.error(entity)
                    if upcoming:
                        bot.pin_chat_message(chat_id=chat, message_id=msg.message_id)
                if upcoming:
                    time_to_broadcast = (video.get('publishedAt') - datetime.utcnow()).total_seconds()
                    func.addBroadcast(video.get("title"), video.get("url"), time_to_broadcast, chats)
            query = update(posts).values(last_yt_video_sent=datetime.utcnow().isoformat()[0:19] + "Z")
            conn.execute(query)
            return True if videos else False
    except Exception as e:
        logging.error(e)
        return False


def send_insta_post(chats):
    try:
        response = conn.execute(select(posts.c.last_insta_post_sent)).fetchone()
        result = repository.get_insta_posts(constants.insta_username, response[0])
        if isinstance(result, Exception):
            # logging.error(result)
            return False
        else:
            for post in result:
                keyboard = InlineKeyboardMarkup(row_width=1)
                keyboard.add(InlineKeyboardButton(text="Like Post on Instagram", url=post[0]))
                msg = "<b>New Instagram Post</b>\n{}".format(post[1])
                for chat in chats:
                    try:
                        bot.send_photo(chat, post[2], caption=msg, reply_markup=keyboard, parse_mode="HTML")
                    except ApiTelegramException:
                        pass
            query = update(posts).values(last_insta_post_sent=datetime.utcnow().isoformat()[0:19] + "Z")
            conn.execute(query)
            return True if result else False
    except Exception as e:
        logging.error(e)
        return False


def send_facebook_posts(chats):
    try:
        response = conn.execute(select(posts.c.last_fb_post_sent)).fetchone()
        result = repository.get_facebook_posts(constants.fb_username, response[0])
        if isinstance(result, Exception):
            # logging.error(result)
            return False
        else:
            for post in result:
                keyboard = InlineKeyboardMarkup(row_width=1)
                keyboard.add(InlineKeyboardButton(text="Like Post on Facebook", url=post.get("url")))
                if post.get('text'):
                    msg = "<b>New Facebook Post</b>\n{}".format(post.get('text'))
                    for chat in chats:
                        if post.get("video") is not None:
                            try:
                                bot.send_video(chat_id=chat, video=post.get("video"), thumb=post.get('video_thumbnail'),
                                               caption=msg, reply_markup=keyboard)
                            except ApiTelegramException:
                                pass
                        elif post.get("images") is not None:
                            try:
                                bot.send_photo(chat, post.get('images')[0], caption=msg, reply_markup=keyboard,
                                               parse_mode="HTML")
                            except ApiTelegramException:
                                bot.send_message(chat, msg, reply_markup=keyboard, parse_mode="HTML")
                            except Exception:
                                pass
            query = update(posts).values(last_fb_post_sent=datetime.utcnow().isoformat()[0:19] + "Z")
            conn.execute(query)
            return True if result else False
    except Exception as e:
        logging.error(e)
        return False


def send_zebrabooking_dj(chats):
    try:
        response = conn.execute(select(posts.c.sent_artists)).fetchone()[0]
        last_artists_sent = json.loads(response)
        events, new_events_fetched = repository.get_future_events(constants.website_url, last_artists_sent)
        if isinstance(events, Exception):
            # logging.error(events)
            return False
        else:
            for event in events:
                msg = f"""<b>New Event on <a href='https://zebrabooking.com'>ZebraBooking</a></b>

<b>Event Name: </b>{event[1]}
<b>Event Venue: </b>{event[2]}
<b>Event City: </b>{event[3]}"""
                keyboard = InlineKeyboardMarkup(row_width=1)
                keyboard.add(InlineKeyboardButton(text="Visit Artist's Page", url=event[4]))
                for chat in chats:
                    try:
                        bot.send_photo(chat, photo=event[0], caption=msg, parse_mode="HTML", reply_markup=keyboard)
                    except ApiTelegramException:
                        pass
            query = update(posts).values(sent_artists=json.dumps(list(set(new_events_fetched))))
            conn.execute(query)
            return True if events else False
    except Exception as e:
        logging.error(e)
        return False


def send_featured_bandcamp_album(chats):
    try:
        response = conn.execute(select(posts.c.featured_albums_sent)).fetchone()[0]
        featured_albums_sent = json.loads(response)
        featured_album, new_albums_fetched = repository.get_featured_bandcamp_albums(featured_albums_sent)
        if isinstance(featured_album, Exception):
            # logging.error(featured_album)
            return False
        else:
            for album in featured_album:
                keyboard = InlineKeyboardMarkup(row_width=1)
                keyboard.add(InlineKeyboardButton(text="Listen on Bandcamp", url=album.get("url")))
                msg = "<b>New Featured Album on Bandcamp</b>\n<a href='{}'>{}</a>" \
                    .format(album.get('url'), album.get('title'))
                for chat in chats:
                    try:
                        msg = bot.send_photo(chat, photo=album.get('img_url'), caption=msg, reply_markup=keyboard,
                                             parse_mode="HTML")
                    except ApiTelegramException:
                        pass
                    bot.pin_chat_message(chat_id=chat, message_id=msg.message_id)
            query = update(posts).values(featured_albums_sent=json.dumps(list(set(new_albums_fetched))))
            conn.execute(query)
            return True if featured_album else False
    except Exception as e:
        logging.error(e)
        return False


def send_new_bandcamp_album(chats):
    try:
        new_album = repository.get_new_bandcamp_albums()
        if isinstance(new_album, Exception):
            # logging.error(new_album)
            return False
        else:
            for album in new_album:
                keyboard = InlineKeyboardMarkup(row_width=1)
                keyboard.add(InlineKeyboardButton(text="Listen on Bandcamp", url=album.get("url")))
                msg = "<b>New Album on Bandcamp</b>\n<a href='{}'>{}</a>".format(album.get('url'), album.get('title'))
                for chat in chats:
                    try:
                        msg = bot.send_photo(chat, photo=album.get('img_url'), caption=msg, reply_markup=keyboard,
                                             parse_mode="HTML")
                    except ApiTelegramException:
                        pass
    except Exception as e:
        logging.error(e)
        return False


def autopost():
    try:
        chats = conn.execute(select(groups.c.chat_id).where(groups.c.autopost == "on")).fetchall()
        chats = [group[0] for group in chats]
        send_yt_videos(chats)
        send_insta_post(chats)
        send_facebook_posts(chats)
        send_zebrabooking_dj(chats)
        send_new_bandcamp_album(chats)
        send_featured_bandcamp_album(chats)
    except Exception as e:
        logging.error(e)


schedule.every().day.at("00:05").do(autopost)


def forever():
    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except Exception as e:
        logging.error(e)


t1 = threading.Thread(target=forever)

t1.start()


@bot.message_handler(chat_types=['private'], commands=['get_id'])
@bot.message_handler(is_admin=True, chat_types=['group', 'supergroup'], commands=['get_id'])
def chat_id(message):
    bot.send_message(message.chat.id, message.chat.id)


@bot.message_handler(is_admin=False, chat_types=['group', 'supergroup'], commands=['config'])
def config_bot_user(message):
    try:
        bot.delete_message(message.chat.id, message.message_id)
    except:
        pass


@bot.message_handler(is_admin=True, chat_types=['group', 'supergroup'], commands=['config'])
def config_bot(message):
    try:
        # token = telebot.util.extract_arguments(message.text).strip()
        try:
            bot.delete_message(message.chat.id, message.message_id)
        except:
            pass
        keyboard = InlineKeyboardMarkup()
        chat_id = message.chat.id
        options = [
            InlineKeyboardButton("Welcome Message", callback_data=f"config_welcome_{chat_id}"),
            InlineKeyboardButton("Captcha Verification", callback_data=f"config_captcha_{chat_id}"),
            InlineKeyboardButton("Subscribe to Contents from Zebra Rec.", callback_data=f"config_autopost_{chat_id}")]
        for option in options:
            keyboard.row(option)
        try:
            bot.send_message(message.from_user.id, f"These are the available options for you for the "
                                                   f"chat <b>{message.chat.title}</b>", reply_markup=keyboard)
        except:
            bot.send_message(message.chat.id, "Before using this command Please Initialize me or"
                                              " Unblock if you have blocked me")
    except Exception as e:
        if bot.get_chat_member(message.chat.id, bot.get_me().id).status not in ['administrator', 'creator']:
            bot.send_message(message.chat.id, MAKE_ME_ADMIN)
        else:
            logging.error(e)


@bot.message_handler(chat_types=['private'], commands=['cancel'])
def delete_operation(message):
    try:
        bot.clear_step_handler(message)
        bot.reply_to(message, "<b>No Operation to Cancel !!</b>")
    except:
        pass


@bot.message_handler(is_admin=False, chat_types=['group', 'supergroup'],
                     commands=['pin', 'unpin', 'unpinall', 'invitelink', 'kick', 'ban', 'mute', 'restrict', 'unmute',
                               'filter', 'remove_filter'])
def admin_only_cmds(message):
    try:
        bot.send_message(message.chat.id, '<b>Only Admin can Execute this Command !!</b>')
    except:
        pass


@bot.message_handler(is_admin=True, chat_types=['group', 'supergroup'], commands=['pin'])
def pin_msg(message):
    try:
        try:
            bot.delete_message(message.chat.id, message.message_id)
        except:
            pass
        replied_msg = message.reply_to_message
        if replied_msg:
            bot.pin_chat_message(message.chat.id, replied_msg.message_id)
            return
        bot.send_message(message.chat.id,
                         'This command is used to pin any message in a chat.\n\n' +
                         'Reply with this command to the message which you want to pin.'
                         )
    except Exception as e:
        if bot.get_chat_member(message.chat.id, bot.get_me().id).status not in ['administrator', 'creator']:
            bot.send_message(message.chat.id, MAKE_ME_ADMIN)
        else:
            logging.error(e)


@bot.message_handler(is_admin=True, chat_types=['group', 'supergroup'], commands=['unpin'])
def unpin_msg(message):
    try:
        try:
            bot.delete_message(message.chat.id, message.message_id)
        except:
            pass
        replied_msg = message.reply_to_message
        if replied_msg:
            bot.unpin_chat_message(message.chat.id, replied_msg.message_id)
            return
        bot.send_message(message.chat.id,
                         'This command is used to unpin any pinned message in a supergroup/group chat.\n\n' +
                         'Reply with this command to the message which you want to unpin.' +
                         ' Be sure to reply to the message which is pinned.'
                         )
    except Exception as e:
        if bot.get_chat_member(message.chat.id, bot.get_me().id).status not in ['administrator', 'creator']:
            bot.send_message(message.chat.id, MAKE_ME_ADMIN)
        else:
            logging.error(e)


@bot.message_handler(is_admin=True, chat_types=['group', 'supergroup'], commands=['unpinall'])
def unpin_all(message):
    try:
        try:
            bot.delete_message(message.chat.id, message.message_id)
        except:
            pass
        bot.unpin_all_chat_messages(message.chat.id)
    except Exception as e:
        if bot.get_chat_member(message.chat.id, bot.get_me().id).status not in ['administrator', 'creator']:
            bot.send_message(message.chat.id, MAKE_ME_ADMIN)
        else:
            logging.error(e)


@bot.message_handler(is_admin=True, chat_types=['group', 'supergroup'], commands=['invitelink'])
def invite_link(message):
    try:
        try:
            bot.delete_message(message.chat.id, message.message_id)
        except:
            pass
        try:
            bot.send_message(message.chat.id,
                             f"Link to join this {message.chat.type} :-\n" +
                             bot.export_chat_invite_link(message.chat.id))
        except ApiTelegramException as error:
            bot.send_message(message.chat.id, string.capwords(error.result_json['description']))
    except Exception as e:
        if bot.get_chat_member(message.chat.id, bot.get_me().id).status not in ['administrator', 'creator']:
            bot.send_message(message.chat.id, MAKE_ME_ADMIN)
        else:
            logging.error(e)


@bot.message_handler(is_admin=True, chat_types=['group', 'supergroup'], commands=['kick', 'ban'])
def kick_user(message):
    try:
        try:
            bot.delete_message(message.chat.id, message.message_id)
        except:
            pass
        replied_msg = message.reply_to_message
        if replied_msg:
            try:
                bot.kick_chat_member(message.chat.id, replied_msg.from_user.id, revoke_messages=True)
                bot.send_message(message.chat.id,
                                 f"{replied_msg.from_user.full_name} is Kicked by {message.from_user.full_name}")
            except ApiTelegramException as error:
                bot.send_message(message.chat.id, string.capwords(error.result_json['description']))
            return
        bot.send_message(message.chat.id,
                         'This command is used to kick/ban a specific user from the group/supergroup chat.\n\n' +
                         'Reply with this command to the message sent by that user whom you want to ban/kick.'
                         )
    except Exception as e:
        if bot.get_chat_member(message.chat.id, bot.get_me().id).status not in ['administrator', 'creator']:
            bot.send_message(message.chat.id, MAKE_ME_ADMIN)
        else:
            logging.error(e)


@bot.message_handler(is_admin=True, chat_types=['group', 'supergroup'], commands=['mute', 'restrict'])
def mute_user(message):
    try:
        try:
            bot.delete_message(message.chat.id, message.message_id)
        except:
            pass
        replied_msg = message.reply_to_message
        if replied_msg:
            try:
                bot.restrict_chat_member(message.chat.id, replied_msg.from_user.id)
                bot.send_message(message.chat.id,
                                 f"{replied_msg.from_user.full_name} is muted by {message.from_user.full_name}")
            except ApiTelegramException as error:
                bot.send_message(message.chat.id, string.capwords(error.result_json['description']))
            return
        bot.send_message(message.chat.id,
                         'This command is used to mute/restrict a specific user in the chat.\n\n' +
                         'Reply with this command to the message sent by that user whom you want to mute.'
                         )
    except Exception as e:
        if bot.get_chat_member(message.chat.id, bot.get_me().id).status not in ['administrator', 'creator']:
            bot.send_message(message.chat.id, MAKE_ME_ADMIN)
        else:
            logging.error(e)


@bot.message_handler(chat_types=['group', 'supergroup'], commands=['report'])
def report_user(message):
    try:
        replied_msg = message.reply_to_message
        if replied_msg:
            try:
                reason = telebot.util.extract_arguments(message.text).strip()
                if len(reason) == 0:
                    bot.send_message(message.chat.id, "Please provide Reason of Reporting!")
                    return
                try:
                    bot.delete_message(message.chat.id, message.message_id)
                except:
                    pass
                bot.send_message(message.chat.id,
                                 f"{message.from_user.full_name} has Reported against {replied_msg.from_user.full_name}"
                                 f"\nReason: {reason}")
                try:
                    bot.send_message(constants.log_grp,
                                     f"{message.from_user.full_name} has Reported against"
                                     f" {replied_msg.from_user.full_name}\nReason: {reason}")
                except:
                    pass
            except ApiTelegramException as error:
                bot.send_message(message.chat.id, string.capwords(error.result_json['description']),
                                 reply_to_message_id=message.message_id)
            return
        bot.send_message(message.chat.id,
                         """<b>[Usage]</b> /report [Reason]
This command is used to report a user in the chat.
Reply with this command to the message sent by that user whom you want to report.""")
    except:
        pass


# Class will check whether the user is admin or creator in group or not
class IsAdmin(telebot.custom_filters.SimpleCustomFilter):
    key = 'is_admin'

    @staticmethod
    def check(message, **kwargs):
        return bot.get_chat_member(message.chat.id, message.from_user.id).status in ['administrator', 'creator']


bot.add_custom_filter(IsAdmin())
