"""
Reply markup keyboards
"""

from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton


def update_config(config_type, value):
    """
    Return the update configuration keyboard of captions/button
    """
    if config_type == 'button':
        msg_text = 'Buttons'
    else:
        msg_text = 'Captions'

    keyboard = InlineKeyboardMarkup()
    if value == 'off':
        keyboard.row(InlineKeyboardButton(f'Turn {msg_text} On', callback_data=f'{config_type}-on'))
    else:
        keyboard.row(InlineKeyboardButton(f'Turn {msg_text} Off', callback_data=f'{config_type}-off'))
    return keyboard
