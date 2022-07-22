import logging

import requests

from zebra_assistant import bot

if __name__ == '__main__':
    bot.remove_webhook()
    try:
        bot.infinity_polling(skip_pending=True, timeout=60)
    except requests.exceptions.Timeout:
        pass
    except Exception as e:
        logging.error(e)
