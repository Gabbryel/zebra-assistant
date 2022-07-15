"""
Main Program Starts Here
"""

# built-in modules
import logging
import os

# need to install these modules
import sqlalchemy as db
from flask import Flask, request
from dotenv import load_dotenv
from telebot import TeleBot
from telebot.types import BotCommand, BotCommandScopeAllPrivateChats, BotCommandScopeAllGroupChats, Update, \
    BotCommandScopeAllChatAdministrators

# files
from config import config
from zebra_assistant.util import Constants


def initialize_bot():
    """
    Initialize bot instance and set webhook
    :return: TeleBot instance
    """
    bot_instance: TeleBot = TeleBot(constants.token, threaded=False, parse_mode='HTML', skip_pending=True)
    return bot_instance


def set_bot_credentials(bot_instance: TeleBot):
    """
    :param bot_instance: TeleBot instance
    setting bot credentials like username, first name, last name, commands, etc.
    """
    bot_info = bot_instance.get_me()
    constants.name = bot_info.first_name
    constants.username = bot_info.username
    constants.admins_dict = config.ADMINS_LIST_DICT
    constants.website_url = config.WEBSITE_URL
    constants.yt_api_key = config.YT_API_KEY
    constants.yt_channel_id = config.YT_CHANNEL_ID
    constants.insta_username = config.INSTA_USERNAME
    constants.fb_username = config.FB_USERNAME

    # deleting all previous commands
    bot_instance.delete_my_commands()

    # set bot commands for all private chats
    bot_instance.set_my_commands(
        commands=[
            BotCommand("config", "Configure Group"),
            BotCommand("check", "Check for any New Posts"),
            BotCommand("pin", "Pin a message"),
            BotCommand("unpin", "Unpin a pinned message"),
            BotCommand("unpinall", "Unpin all pinned messages"),
            BotCommand("invitelink", "Show Group Invite link"),
            BotCommand("kick", "Kick/ban a user"),
            BotCommand("mute", "Mute/restrict a user"),
            BotCommand("unmute", "Unmute a muted user"),
            BotCommand("report", "Report bad person or scammer ")
        ],
        scope=BotCommandScopeAllChatAdministrators()  # use for all group chats admin
    )

    # add commands for all group chats
    bot_instance.set_my_commands(
        commands=[BotCommand("report", "Report bad person or scammer ")],
        scope=BotCommandScopeAllGroupChats()  # use for all group chats
    )

    bot_instance.set_my_commands(
        commands=[BotCommand("start", "Initialize the bot")],
        scope=BotCommandScopeAllPrivateChats()
    )


load_dotenv()

webhook = False
constants = Constants(os.getenv('BOT_TOKEN'), os.getenv('HOST_NAME'))  # get token from @BotFather
bot = initialize_bot()
set_bot_credentials(bot)

# database setup
DB_FILE = os.getenv('DATABASE_URL')
DB_FILE = DB_FILE.replace('postgres://', 'postgresql://')
engine = db.create_engine(DB_FILE, connect_args={'check_same_thread': False}, echo=True)
conn = engine.connect()
metadata = db.MetaData()
groups = db.Table('groups_config', metadata, autoload=True, autoload_with=engine)
posts = db.Table('posts_config', metadata, autoload=True, autoload_with=engine)

# setup logging
logging.basicConfig(level=logging.ERROR, filemode='a',
                    format='%(asctime)s : %(levelname)s - '
                           '%(funcName)s (%(filename)s) Function - %(message)s')

# require to connect files with each other
from zebra_assistant import func, group_features, commandHandler
func.get_group_configuration()


# For running without polling method
if webhook:
    bot.remove_webhook()
    bot.set_webhook(url=constants.webhook_url, drop_pending_updates=True)
    app = Flask(__name__)


    @app.route('/' + os.getenv('BOT_TOKEN'), methods=['POST'])
    def set_webhook():
        """
        Setting webhook for bot
        """
        update = Update.de_json(
            request.stream.read().decode('utf-8'))
        bot.process_new_updates([update])
        return 'ok', 200


    @app.route('/')
    def home():
        """
        Home page of the web server
        """
        return "Bot is Running ..."
