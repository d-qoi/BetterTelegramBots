import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, MessageHandler
from telegram.ext.filters import Filters

from customFilters import GroupAddCheckFilter, CheckAdminGroup


class AdminGroupHandler(object):
    BOT = None
    MDB = None
    DP = None

    admin_group = None
    group_config = None

    logger = logging.getLogger(__name__)

    admin_group_welcome_text = """
This group is now set as an admin group.

If you want this bot to work in your groups remember to add me to the group, or add your own bot and send the bot's code to me.

Send /config to change settings for all of your chats.
"""

    def __init__(self, dp, bot, MDB):
        self.BOT = bot
        self.MDB = MDB
        self.DB = dp

        self.master_goroup = self.MDB.admin_group
        self.group_config = self.MDB.group_config

        self.gacf = GroupAddCheckFilter(self.admin_group, self.group_config, GroupAddCheckFilter.ADMIN_GROUP)
        self.cag = CheckAdminGroup(self.admin_group)

        dp.add_handler(MessageHandler(self.gacf,
                                      self.welcome_new_chat),
                       group=2)

        dp.add_handler(MessageHandler(Filters.new_chat_member & self.cag,
                                      self.welcome_new_member),
                       group=2)

        dp.add_handler(CommandHandler('config',
                                      self.config,
                                      filters=self.cag),
                       group=2)

        dp.add_handler(CallbackQueryHandler(self.setAdminsCallback,
                                            pattern="agh sa (-?[0-9]+) ([0-9]+) ([0-9]+)",
                                            pass_groups=True),
                       group=2)
        dp.add_handler(CallbackQueryHandler(self.setNotificationsCallback,
                                            pattern="agh sn (-?[0-9]+) ([0-9]+) ([0-9]+)",
                                            pass_groups=True),
                       group=2)
        dp.add_handler(CallbackQueryHandler(self.closeConfigCallback,
                                            pattern="agh cc (-?[0-9]+) ([0-9]+) ([0-9]+)",
                                            pass_groups=True),
                       group=2)

    def __createMainMenu(self, chat_id, user_id, group_id):
        chat_user_id = "%d %d %d" % (chat_id, user_id, group_id)
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
            InlineKeyboardButton("Group Settings",
                                 callback_data="agh gs %s" % chat_user_id)
        ])
        keyboard.append([
            InlineKeyboardButton("Set Black/White lists",
                                 callback_data="agh sbl %s" % chat_user_id)
        ])
        keyboard.append([
            InlineKeyboardButton("Set Flood Limits",
                                 callback_data="agh sfl %s" % chat_user_id)
        ])
        keyboard.append([
            InlineKeyboardButton("Close config",
                                 callback_data="agh cc %s" % chat_user_id)
        ])
        return InlineKeyboardMarkup(keyboard)

    def __create_chat_select_menu(self, chat_id, user_id, offset):
        chat_user_id = "%d %d %d" % (chat_id, user_id, offset)
        result = self.group_config.find({"admins": user_id})
        keyboard = []
        if not result:
            return None
        for i in range(offset, offset + 10 if offset + 10 < result.count() else result.count()):
            keyboard.append([
                InlineKeyboardButton(result[i].group_title,
                                     callback_data="agh sg %d %s" % (i, chat_user_id))])

    def setNotificationsCallback(self, bot, update, groups):
        pass

    def setAdminsCallback(self, bot, update, groups):
        pass

    def closeConfigCallback(self, bot, update, groups):
        pass

    def welcome_new_chat(self, bot, update):
        """
The filter handles checking to make sure the admin_group_link is correct.
Don't need to check it twice.
"""
        message = update.effective_message
        chat = update.effective_chat
        self.admin_group.find_one_and_update(
            {
                "admin_id": message.from_user.id
            },
            {
                "group_id": chat.id,
                "admin_group_link": ""
            })
        self.cag.update_cache_for(chat.id)
        update.reply_text(self.admin_group_welcome_text)

    def welcome_new_member(self, bot, update):
        pass

    def config(self, bot, update):
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        keyboard = self.__createMainMenu(chat_id, user_id)

        text = "Config menu for %s %s\n" % (
            update.effective_user.first_name, update.effective_user.last_name)

        msg = bot.send_message(chat_id, text, reply_markup=keyboard)
