import logging
import string

from random import choices
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, MessageHandler
from telegram.ext.filters import Filters
from pymongo.collection import ReturnDocument

from customFilters import MGFilter


class MasterGroupHandler(object):
    bot = None
    MDB = None
    DP = None

    admin_group = None

    logger = logging.getLogger(__name__)

    WELCOMETEXT = """
Welcome to the Master Group for %s, %s %s.

Clicking the button will create a single use code.

Sending this code to a group will set the group as either your admin group or a group you would like this bot to act in.

You will need to create a new code to add another group, and you need to send the message to the group.

Only one admin per bot network should be in this chat. If that admin needs to change, talk to @ytkileroy.



Admin Group Link: %s
Other Group Link: %s
"""
    FAQTEXT = """
General:
    Group passwords can only be used once. They need to be regenerated after each use.
Admin groups:
    Multiple bot networks can be handled with one admin group.

    Multiple bot networks from one admin group can have seperate admins.

    Only the creator of the bot network can set admins for their network.
"""

    def __init__(self, dp, bot, MDB):
        self.logger.debug("Initializing")
        self.bot = bot
        self.MDB = MDB
        self.DP = dp

        self.admin_group = self.MDB.admin_group

        mgf = MGFilter(self.MDB.global_config)

        dp.add_handler(CommandHandler("setmastergroupplz", self.set_admin_group),
                       group=3)
        dp.add_handler(CommandHandler("get_group_links", self.welcome_new_member,
                                      filters=mgf),
                       group=3)
        dp.add_handler(MessageHandler(Filters.status_update.new_chat_members & mgf,
                                      self.welcome_new_member),
                       group=3)
        dp.add_handler(CallbackQueryHandler(self.group_link_handler,
                                            pattern="mgh (cal|col) (-?[0-9]+) ([0-9]+)",
                                            pass_groups=True),
                       group=3)
        self.logger.info("Done Initializing")

    def _gen_password(self):
        self.logger.debug("_gen_password entered")
        return ''.join(choices(string.ascii_letters + string.digits, k=20))

    def set_admin_group(self, bot, update):
        self.logger.debug("set_admin_group entered")
        self.logger.warn("Set_admin_group called")
        res = self.MDB.global_config.find_one({})
        if res:
            return
        self.MDB.global_config.insert_one({
            "group": update.effective_chat.id
            })
        update.message.reply_text("Master Group Set")
        self.logger.warn("master group set to: %s" % str(update.effective_chat))

    def welcome_new_member(self, bot, update):
        self.logger.debug("welcome_new_member entered")
        if update.message.new_chat_members:
            user = update.message.new_chat_members[0]
            self.logger.debug("new_chat_member[0]")
        else:
            user = update.effective_user
            self.logger.debug("effective_user")
        self.logger.info("welcome_new_member called for: %s" % str(user))

        res = self.admin_group.find_one({"admin_id": user.id})
        if not res:
            res = {"admin_id": user.id}
            self.admin_group.insert_one(res)
        else:
            if 'link_msg_id' in res:
                msg_id = res['link_msg_id']
                chat_id = update.effective_chat.id
                bot.edit_message_text("Please use new message", chat_id=chat_id, message_id=msg_id)

        text = self.WELCOMETEXT % (self.bot.name,
                                   user.first_name,
                                   user.last_name,
                                   res.get('admin_group_link', ''),
                                   res.get('other_group_link', ''))

        chat_user_id = "%d %d" % (update.effective_chat.id, user.id)
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("Create Admin Group Link",
                                  callback_data="mgh cal %s" % (chat_user_id))],
            [InlineKeyboardButton("Create Other Group Link",
                                  callback_data="mgh col %s" % (chat_user_id))]])
        new_msg = update.message.reply_text(text, reply_markup=markup)

        res = self.admin_group.update_one({"admin_id": user.id},
                                           {"$set": {"link_msg_id": new_msg.message_id}})

    def group_link_handler(self, bot, update, groups):
        self.logger.debug("Group Link Handler called with groups: %s" % str(groups))
        password = self._gen_password()
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        if groups[1:] != (str(chat_id), str(user_id)):
            update.callback_query.answer(
                text="Please use your own group links",
                show_allert=True)
            return

        if groups[0] == 'col':
            res = self.admin_group.find_one_and_update({"admin_id": update.effective_user.id},
                                                       {"$set": {"other_group_link": password}},
                                                       return_document=ReturnDocument.AFTER)
        elif groups[0] == 'cal':
            res = self.admin_group.find_one_and_update({"admin_id": update.effective_user.id},
                                                       {"$set": {"admin_group_link": password}},
                                                       return_document=ReturnDocument.AFTER)
        else:
            update.callback_query.message.reply_text("Something went wrong in group_link_handler", quote=False)
            self.logger.error("Something went really wrong in group_link_handler: %s" % str(groups))
        if not res:
            update.callback_query.message.reply_text("No admin_group found for group.", quote=False)
            self.logger.error("No admin_group found for user clocking link: %s" % str(update.effective_user))
            update.callback_query.answer()
            return

        text = self.WELCOMETEXT % (self.bot.name,
                                   update.effective_user.first_name,
                                   update.effective_user.last_name,
                                   res.get('admin_group_link', ''),
                                   res.get('other_group_link', ''))
        chat_user_id = "%d %d" % (update.effective_chat.id, update.effective_user.id)
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("Create Admin Group Link",
                                  callback_data="mgh cal %s" % (chat_user_id))],
            [InlineKeyboardButton("Create Other Group Link",
                                  callback_data="mgh col %s" % (chat_user_id))]])
        update.callback_query.message.edit_text(text, reply_markup=markup)
        update.callback_query.answer()
