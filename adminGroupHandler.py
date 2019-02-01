import logging
from collections import defaultdict

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, MessageHandler
from telegram.ext.filters import Filters

from pymongo import ReturnDocument

from customFilters import GroupAddCheckFilter, CheckAdminGroup

# Order of Menus
"""
/unset_admin_group -- unsets the admin group

/config -> 
Get Group Link -> create message that can be forwarded, ends conversation
Default settings -> Changes settings in the admin group menu
Group Specific Settings -> select group menu
    
Default settings ->
    Revert all -> confirm -> end
    Revert Group -> select group -> end
    Settings...

Settings:
    See Main Menu in methods    

select_group inline menu:
next or previous (agh sg [np] offset chat_id user_id) -> select_group menu
chat_selected (agh sg chosen_group chat_id user_id) -> group_config menu

group_config menu
set_admins -> set_admins menu (agh sa chosen_group chat_id user_id)
set_notifications -> set_notifications menu (agh sn chosen_group chat_id user_id)
group_settings -> group_settings menu (agh gs chosen_group chat_id user_id)
set_blacklists -> set_blacklists menu (agh sb chosen_group chat_id user_id)
set_flood_limits -> set_flood_limits menu (agh sfl chosen_group chat_id user_id)
close_menu -> (agh cc chosen_group chat_id user_id)

set_admins:
admins (agh a admin_id chosen_group chat_id user_id) may be too long, double check

set_notifications:

set_admins menu (agh sa


"""

ADMIN_GROUP_WELCOME_TEXT = """
This group is now set as an admin group.

If you want this bot to work in your groups remember to add me to the group, or add your own bot and send the bot's code to me.

Send /config to change settings for all of your chats.
"""

CONFIG_CHAT_SELECT_TEXT = """
Please select the chat you would like to configure.
"""

NOT_AN_ADMIN_RESPONSE = """
You are not an admin of any network this chat serves.

Please talk to @YTKileroy if you want to make a network.
    """

CONFIG_MENU_TEXT = """
Config menu for %s %s

"""

RESET_GROUPS_CONFIRM_TEXT = """
Reset all groups in the %s network to use default settings?

This action is irreversible, are you sure you want to continue?
"""
RESET_GROUPS_CONFIRMATION = """
All groups are now using default settings.
"""

NETWORK_SELECT_TEXT = """
Please select the network you would like to open the config menu for.
"""

RESET_GROUP_NO_GROUPS_TEXT = """
All groups are using default settings.
"""
RESET_GROUP_SELECT_GROUP_TEXT = """
Please select the group you would like to reset.
"""

CLOSE_CONFIG = InlineKeyboardButton("Close Config Menu", callback_data="agh cc")

HEADER_TEXT = "header text"
TEXT = "text"
NETWORK = "network"
USER_ID = "user_id"
CHAT_ID = "chat_id"
MESSAGE_ID = "msg_id"
STATE = "state"

GROUP_LIST_LIMIT = 5

class AdminGroupHandler(object):
    BOT = None
    MDB = None
    DP = None

    admin_group = None
    group_config = None

    logger = logging.getLogger(__name__)

    def __init__(self, dp, bot, MDB):
        self.BOT = bot
        self.MDB = MDB
        self.DB = dp

        self.admin_group = self.MDB.admin_group
        self.group_config = self.MDB.group_config
        self.conversation_db = self.MDB.ahg_concersations

        self.group_add_check_filter = GroupAddCheckFilter(self.admin_group, self.group_config,
                                                          GroupAddCheckFilter.ADMIN_GROUP)
        self.cag = CheckAdminGroup(self.admin_group)

        self.conversation_data = defaultdict(dict)

        dp.add_handler(MessageHandler(self.group_add_check_filter,
                                      self.welcome_new_chat),
                       group=2)

        dp.add_handler(MessageHandler(Filters.status_update.new_chat_members & self.cag,
                                      self.welcome_new_member),
                       group=2)

        dp.add_handler(CommandHandler('config',
                                      self.config,
                                      filters=self.cag),
                       group=2)

        dp.add_handler(CallbackQueryHandler("agh ([a-z]+)([0-9]*)",
                                            self.callback_switch,
                                            pass_groups=True),
                       group=2)

        self.__reload_cache()
        self.logger.info("Done Initializing")

    def __reload_cache(self):
        self.logger.info("Admin Handler Cache Reloading")
        cursor = self.conversation_db.find({})
        for conversation in cursor:
            index = (conversation[MESSAGE_ID], conversation[CHAT_ID])
            self.conversation_data[index] = conversation
        self.logger.debug("cache reloaded: %d" % len(self.conversation_data))

    def __save_state(self, msg_id, chat_id):
        """
        :param msg_id: Message ID
        :param chat_id: Chat ID of the chat to save
        :return: None

        Save everything to a Mongo document
        """
        self.logger.debug("save state")
        if (msg_id, chat_id) not in self.conversation_data:
            return

        self.conversation_db.update_one({MESSAGE_ID: msg_id, CHAT_ID: chat_id},
                                        self.conversation_data[(msg_id, chat_id)],
                                        upsert=True)

    def callback_switch(self, bot, update, groups):
        self.logger.debug("Callback Switch entered")
        user_id = update.callback_query.from_user.id
        chat_id = update.callback_query.message.chat.id
        msg_id = update.callback_query.message.id

        if ((msg_id, chat_id) not in self.conversation_data and
                self.conversation_data[USER_ID] != user_id):
            update.callback_query.answer("Please don't use other user's menu.")
            return

        conversation = (msg_id, chat_id)
        point = groups[0]

        if point == "cc":
            self.close_config(bot, update)

        if conversation[STATE] == "ns":
            res = self.admin_group.find({"group_id": chat_id,
                                         "admins": user_id}).sort("network", 1)
            res = list(res)
            if len(res) <= int(groups[1]):
                self.conversation_data[(msg_id, chat_id)]["network"] = res[int(groups[1])]
            self.create_main_menu(bot, update)

        elif conversation[STATE] == "mm":
            if point == "ra":
                if groups(1):
                    self.reset_all(bot, update)
                else:
                    self.reset_all_confirm(bot, update)
            elif point == "rg":
                self.reset_group_start(bot, update)
            elif point == "gs":
                pass
            elif point == "as":
                pass
            else:
                self.logger.error("main menu error, received point %s" % point)
                update.callback_query.answer("Something went wrong, please try again.")
                self.close_config(bot, update)

        elif conversation[STATE] == "rg":
            if point == "sg":
                pass
            elif point == "cg":
                pass
            elif point == "ng":
                pass
            elif point == "pg":
                pass
            else:
                self.logger.error("reset group error, received point %s" % point)
                update.callback_query.answer("Something went wrong, please try again.")
                self.close_config(bot, update)

        self.__save_state(msg_id, chat_id)

    def create_main_menu(self, bot, update, extra_text=""):
        """
        Creates the main menu using the current message.
        Sets the state of the conversation to "mm" (main menu)

        :param bot: The telegram bot
        :param update: The update to process
        :param extra_text: Defaults to empty string, string to be appended to usual message.
        :return: None
        """
        user_id = update.callback_query.from_user.id
        chat_id = update.callback_query.message.chat.id
        msg_id = update.callback_query.message.id

        data = self.conversation_data[(msg_id, chat_id)]
        data["point"] = "mm"

        keyboard = [
            [InlineKeyboardButton("Revert All to Default", callback_data="agh ra")],
            [InlineKeyboardButton("Revert Group to default", callback_data="agh rg")],
            [InlineKeyboardButton("Group Settings", callback_data="agh gs")],
            [InlineKeyboardButton("All Settings", callback_data="agh as")],
            [CLOSE_CONFIG]
        ]

        data[TEXT] = CONFIG_CHAT_SELECT_TEXT
        if extra_text:
            data[TEXT] = data[TEXT] + "\n\n" + extra_text

        text = data[HEADER_TEXT]+data[TEXT]
        update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    def reset_all_confirm(self, bot, update):
        """
        Confirms the reset before actually resetting.
        Does not update the state of the conversation.

        :param bot: the bot
        :param update: the update to process
        :return: None
        """
        chat_id = update.callback_query.message.chat.id
        msg_id = update.callback_query.message.id
        data = self.conversation_data[(msg_id, chat_id)]
        keyboard = [
            [InlineKeyboardButton("Reset All Groups (irreversible)", callback_data="agh rg1")]
            [CLOSE_CONFIG]
        ]
        data[TEXT] = RESET_GROUPS_CONFIRM_TEXT%data[NETWORK]
        update.callback_query.edit_message_text(data[HEADER_TEXT]+data[TEXT],
                                                reply_markup=InlineKeyboardMarkup(keyboard))

    def reset_all(self, bot, update):
        """
        Returns to the main menu, calling the main menu function.
        :param bot: The bot
        :param update: The Update to process
        :return: None
        """
        user_id = update.callback_query.from_user.id
        chat_id = update.callback_query.message.chat.id
        msg_id = update.callback_query.message.id
        agd = self.admin_group.find_one({"admins": user_id,
                                         "network": self.conversation_data[(msg_id, chat_id)][NETWORK]})
        if not agd:
            self.close_config(bot, update)
            return

        res = self.group_config.update_many({"admin_group_id": agd["_id"]},
                                            {"$unset":
                                                {
                                                     "rules": "",
                                                     "welcome": "",
                                                     "alerts": "",
                                                     "flood_stkr": "",
                                                     "flood msg": "",
                                                     "flood_link": "",
                                                     "flood_image": ""
                                                 },
                                            "$set":
                                                {
                                                    "default": True
                                                }
                                            })

        self.create_main_menu(bot, update, extra_text=RESET_GROUPS_CONFIRMATION)

    def reset_group_start(self, bot, update):
        """
        Reset group menu start:
        Sets conversation state to rg
        :param bot:
        :param update:
        :return:
        """
        self.logger.debug("reset_group_start called")

        user_id = update.callback_query.from_user.id
        chat_id = update.callback_query.message.chat.id
        msg_id = update.callback_query.message.id
        data = self.conversation_data[(msg_id, chat_id)]

        data[STATE] = "rg"
        keyboard = []

        agd = self.admin_group.find_one({"admins": user_id,
                                         "network": data[NETWORK]})
        if not agd:
            self.close_config(bot, update)
            return

        res = self.group_config.find({"admin_group_id": agd["_id"],
                                      "default": True}).sort("group_title", 1)
        res = list(res)
        if not len(res):
            self.create_main_menu(bot, update, extra_text=RESET_GROUP_NO_GROUPS_TEXT)
            return

        if len(res) <= GROUP_LIST_LIMIT:
            for i in range(len(res)):
                keyboard.append([
                    InlineKeyboardButton(res[i]["group_title"], callback_data="agh sg%d" % i)
                ])
        else:
            for i in range(GROUP_LIST_LIMIT):
                keyboard.append([
                    InlineKeyboardButton(res[i]["group_title"], callback_data="agh sg%d" % i)
                ])
            keyboard.append([
                InlineKeyboardButton("Next Set", "agh ng")
            ])

        data[TEXT] = RESET_GROUP_SELECT_GROUP_TEXT
        text = data[HEADER_TEXT] + data[TEXT]
        update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    def reset_group_select_group(self, bot, update, groups):
        """
        Create the confirmation menu for resetting groups
        Does not change state.
        :param bot: The bot
        :param update: The update to process
        :param groups: The groups from the callback query matching regex
        :return: None
        """

    def close_config(self, bot, update):
        pass

    def welcome_new_chat(self, bot, update):
        self.logger.debug("Welcome new chat called")
        """
The filter handles checking to make sure the master_group_link is correct.
Don't need to check it twice.
"""
        message = update.effective_message
        chat = update.message.chat
        res = self.admin_group.find_one_and_update(
            {
                "admin_id": message.from_user.id
            },
            {"$set": {"group_id": chat.id},
             "$unset": {"admin_group_link": ""}},
            return_document=ReturnDocument.AFTER)
        if not res:
            self.logger.warning("Unable to find the group document")
        self.cag.update_cache_for(chat.id)
        bot.send_message(chat.id, self.ADMIN_GROUP_WELCOME_TEXT)
        self.logger.info("new chat added")

    def welcome_new_member(self, bot, update):
        pass

    def config(self, bot, update):
        """
        Create the initial config menu for the network
        Two potential states:
        * ns (network select)
        * mm (main menu)

        :param bot: The bot, passed by the handler
        :param update: The update to process
        :return: None
        """
        self.logger.debug("config called for %s %d in %d" %
                          (update.effective_user.username, update.effective_user.id, update.message.chat.id))

        user_id = update.effective_user.id
        chat_id = update.message.chat.id
        data = dict()

        res = self.admin_group.find({"group_id": chat_id,
                                     "admins": user_id}).sort("network", 1)
        res = list(res)

        if not len(res):  # count is zero
            update.message.reply_text()

        data[USER_ID] = user_id
        data[CHAT_ID] = chat_id
        data[HEADER_TEXT] = CONFIG_MENU_TEXT % (
            update.effective_user.first_name, update.effective_user.last_name)

        if len(res) > 1:
            # this makes the assumption that there will be less than 5 or 6 networks in any one admin group.
            data[STATE] = "ns"
            keyboard = []
            for i in range(len(res)):
                keyboard.append([InlineKeyboardButton(res[i][NETWORK], callback_data="ahg ns%d" % i)])
            keyboard.append([CLOSE_CONFIG])

            data[TEXT] = NETWORK_SELECT_TEXT

            text = data[HEADER_TEXT] + data[TEXT]

        else:  # there is only one network
            data[STATE] = "mm"
            data[NETWORK] = res[0][NETWORK]

            keyboard = [
                [InlineKeyboardButton("Revert All to Default", callback_data="agh ra")],
                [InlineKeyboardButton("Revert Group to default", callback_data="agh rg")],
                [InlineKeyboardButton("Group Settings", callback_data="agh gs")],
                [InlineKeyboardButton("All Settings", callback_data="agh as")],
                [CLOSE_CONFIG]
            ]

            data[TEXT] = CONFIG_CHAT_SELECT_TEXT

            text = data[HEADER_TEXT] + data[TEXT]

        msg = bot.send_message(chat_id, text, reply_markup=InlineKeyboardMarkup(keyboard))

        self.logger.debug("new message id: %d" % msg.id)

        data[MESSAGE_ID] = msg.id

        self.conversation_data[(msg.id, chat_id)] = data
        self.__save_state(msg.id, chat_id)
