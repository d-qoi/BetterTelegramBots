import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler


class adminGroupHandler(object):
    bot = None
    MDB = None
    logger = logging.getLogger(__name__)

    def __init__(self, dp, bot, MDB):
        self.bot = bot
        self.MDB = MDB

        dp.add_handler(CommandHandler('set_admin_group', self.setAdminGroup))
        dp.add_handler(CommandHandler('config', self.config))

        dp.add_handler(CallbackQueryHandler(self.setAdminsCallback,
                                            pattern="agh sa (-?[0-9]+) ([0-9]+)",
                                            pass_groups=True))
        dp.add_handler(CallbackQueryHandler(self.setNotificationsCallback,
                                            pattern="agh sn (-?[0-9]+) ([0-9]+)",
                                            pass_groups=True))

    def __createMainMenu(self, chat_id, user_id):
        chat_user_id = "%d %d" % (chat_id, user_id)
        keyboard = []
        keyboard.append([
            InlineKeyboardButton("Set Admins",
                                 callback_data="agh sa %s" % chat_user_id)
        ])
        keyboard.append([
            InlineKeyboardButton("Set notifications",
                                 callback_data="agh sn %s" % chat_user_id)
        ])
        return InlineKeyboardMarkup(keyboard)

    def __getAdmins(self, chat_id):
        pass

    def setAdminGroup(self, bot, update):
        pass

    def config(self, bot, update):
        pass

    def setNotificationsCallback(self, bot, update, groups):
        pass

    def setAdminsCallback(self, bot, update, groups):
        pass
