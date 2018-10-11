import logging
import string

from random import Random
from telegarm import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, MessageHandler
from telegram.ext.filters import Filters
from pymongo.collection import ReturnDocument

PASSWORD_LETTERS = string.ascii_letters + string.digits


class MasterGroupHandler(object):
    BOT = None
    MDB = None
    DP = None

    master_group = None

    logger = logging.getLogger(__name__)

    WELCOMETEXT = """
Welcome to the Master Group for


Clicking the button will create a single use code.

Sending this code to a group will set the group as either your admin group or a group you would like this bot to act in.

You will need to create a new code to add another group.

Only one admin of the admin group should be in this chat. If that admin needs to change, talk to @ytkileroy.



Admin Group Link: %s
Other Group Link: %s
"""

    class MGFilter(Filters.BaseFilter):
        name = "master_group_filter"
        group_id = None

        def __init__(self):
            self._update_cache()

        def _update_cache(self):
            if not self.group_id:
                res = self.global_config.find_one()
                if res:
                    self.group_id = res['group']

        def filter(self, message):
            self._update_cache()
            return message.chat.id == self.group_id

    def __init__(self, dp, bot, MDB):
        self.BOT = bot
        self.MDB = MDB
        self.DP = dp

        self.master_group = self.MDB.master_group

        mgf = self.MGFilter()

        dp.add_handler(CommandHandler("setmastergroupplz", self.set_master_group))
        dp.add_handler(CommandHandler("get_group_links", self.welcome_new_member,
                                      filter=mgf))
        dp.add_handler(MessageHandler(Filters.status_update & mgf, self.welcome_new_member))
        dp.add_handler(CallbackQueryHandler(self.group_link_handler,
                                            pattern="mgh (cal|col) (-?[0-9]+) ([0-9]+)",
                                            pass_group=True, group=1))

    def _gen_password(self):
        return ''.join(Random.choices(PASSWORD_LETTERS, k=20))

    def set_master_group(self, bot, update):
        res = self.MDB.global_config.find_one({})
        if res:
            return
        self.MDB.global_config.insert_one({
            "group": update.effective_chat.id
            })
        update.message.reply_text("Master Group Set")

    def welcome_new_member(self, bot, update):
        chat_user_id = "%d %d" % (update.effective_chat.id, update.effective_user.id)
        res = self.master_goup.find_one({"admin_id": update.effective_user.id}, upsert=True)

        text = self.WELCOMETEXT % (self.bot.name, res.get('admin_group_link', ''), res.get('other_group_link', ''))

        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("Create Admin Group Link",
                                  callback_data="mgh cal %s" % (chat_user_id))],
            [InlineKeyboardButton("Create Other Group Link",
                                  callback_data="mgh col %s" % (chat_user_id))]])
        new_msg = update.message.reply_text(text, reply_markup=markup)

        res = self.master_group.update_one({"admin_id": update.effective_user.id},
                                           {"$set": {"link_msg_id": new_msg.id}})

    def group_link_handler(self, bot, update, groups):
        password = self._gen_password()
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        if groups[1:] != (str(chat_id), str(user_id)):
            update.callback_query.answer(
                text="Please use your own group links",
                show_allert=True)
            return

        if groups(0) == 'col':
            res = self.master_goup.find_one({"admin_id": update.effective_user.id},
                                            {"$set": {"other_group_link": password}},
                                            return_document=ReturnDocument.AFTER)
        elif groups(0) == 'cal':
            res = self.master_goup.find_one({"admin_id": update.effective_user.id},
                                            {"$set": {"admin_group_link": password}},
                                            return_document=ReturnDocument.AFTER)
        else:
            update.callback_query.message.reply_text("Something went wrong in group_link_handler", quote=False)
        if not res:
            update.callback_query.message.reply_text("No master_group found for group.", quote=False)
            update.callback_query.answer()
            return

        text = self.WELCOMETEXT % (self.bot.name, res.get('admin_group_link', ''), res.get('other_group_link', ''))
        update.callbac_query.message.edit_text(text)
        update.callback_query.answer()

    def admin_group_link_handler(self, bot, update, groups):
        pass
