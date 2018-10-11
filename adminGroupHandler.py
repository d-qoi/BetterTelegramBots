import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler
from telegram.ext.filters import Filters


class AdminGroupHandler(object):
    BOT = None
    MDB = None
    DP = None

    admins_col = None
    config_col = None

    logger = logging.getLogger(__name__)

    def __init__(self, dp, bot, MDB):
        self.BOT = bot
        self.MDB = MDB
        self.DB = dp

        self.admins_col = self.MDB.admins
        self.config_col = self.MDB.config_col

        dp.add_handler(CommandHandler('set_admin_group', self.setAdminGroup,
                                      filters=Filters.group))

        dp.add_handler(CommandHandler('config', self.config))

        dp.add_handler(CallbackQueryHandler(self.setAdminsCallback,
                                            pattern="agh sa (-?[0-9]+) ([0-9]+)",
                                            pass_groups=True), group=1)
        dp.add_handler(CallbackQueryHandler(self.setNotificationsCallback,
                                            pattern="agh sn (-?[0-9]+) ([0-9]+)",
                                            pass_groups=True), group=1)
        dp.add_handler(CallbackQueryHandler(self.closeConfigCallback,
                                            pattern="agh cc (-?[0-9]+) ([0-9]+)",
                                            pass_groups=True), group=1)

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
        keyboard.append([
            InlineKeyboardButton("Close config",
                                 callback_data="agh cc %s" % chat_user_id)
        ])
        return InlineKeyboardMarkup(keyboard)

    def __getAdmins(self, chat_id):
        result = self.config_col.find_one({'chat_id':chat_id})
        return result['admins']

    def __getAdminDoc(self, user_id):
        result = self.admins_col.find_one({'user_id':user_id})
        return result

    def __checkAdminGroupDefined(self):
        result = self.config_col.find_one({"admin_chat_id":{"$exists":True}})
        if result:
            return True
        return False

    def setAdminGroup(self, bot, update):
        if self.__checkAdminGroupDefined():
            return
        admin_group = {}
        admin_group['title'] = update.effective_chat.title
        admin_group['chat_id'] = update.effective_chat.chat_id
        admin_group['admins'] = [update.effective_user.id]
        self.config_col.insert_one(admin_group)
        self.config_col.insert_one({"admin_chat_id":update.effective_chat.chat_id})

        update.effective_message.reply_text(
"""%s has been set as the admin group for %s.

send /config to change the settings of this bot.""" % (
            update.effective_chat.title, bot.name), quote=False)

    def config(self, bot, update):
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        keyboard = self.__createMainMenu(chat_id, user_id)

        text = "Config menu for %s %s\n" % (
            update.effective_user.first_name, update.effective_user.last_name)

        msg = bot.send_message(chat_id, text, reply_markup=keyboard)

        self.config_col.update_one({"active_admin_config":True},
                                   {"message_list":{"$addToSet":msg.id}},
                                   upsert=True)

    def setNotificationsCallback(self, bot, update, groups):
        pass

    def setAdminsCallback(self, bot, update, groups):
        pass

    def closeConfigCallback(self, bot, update, groups):
        pass
