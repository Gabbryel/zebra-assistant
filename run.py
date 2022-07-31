import logging
from time import sleep

import requests
from telebot.apihelper import ApiTelegramException

from zebra_assistant import bot, constants

if __name__ == '__main__':
    bot.remove_webhook()
    try:
        bot.polling(skip_pending=True, non_stop=True)
    except ApiTelegramException as e:
        bot.send_message(chat_id=constants.log_grp, text=e.description)
    except requests.exceptions.Timeout:
        sleep(5)
    except Exception as e:
        logging.error(e)
