import logging
import string

from random import choices
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, MessageHandler
from telegram.ext.filters import Filters, BaseFilter
from pymongo.collection import ReturnDocument


class MasterGroupHandler(object):
    bot = None
    MDB = None
    DP = None

    master_group = None

    logger = logging.getLogger(__name__)

    WELCOMETEXT = """
Welcome to the Master Group for %s, %s %s.

Clicking the button will create a single use code.

Sending this code to a group will set the group as either your admin group or a group you would like this bot to act in.

You will need to create a new code to add another group.

Only one admin of the admin group should be in this chat. If that admin needs to change, talk to @ytkileroy.



Admin Group Link: %s
Other Group Link: %s
"""

    class MGFilter(BaseFilter):
        name = "master_group_filter"
        group_id = None
        global_config = None

        def __init__(self, global_config):
            self.global_config = global_config
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
        self.bot = bot
        self.MDB = MDB
        self.DP = dp

        self.master_group = self.MDB.master_group

        mgf = self.MGFilter(self.MDB.global_config)

        dp.add_handler(CommandHandler("setmastergroupplz", self.set_master_group))
        dp.add_handler(CommandHandler("get_group_links", self.welcome_new_member,
                                      filters=mgf))
        dp.add_handler(MessageHandler(Filters.status_update & mgf, self.welcome_new_member))
        dp.add_handler(CallbackQueryHandler(self.group_link_handler,
                                            pattern="mgh (cal|col) (-?[0-9]+) ([0-9]+)",
                                            pass_groups=True))

    def _gen_password(self):
        return ''.join(choices(string.ascii_letters + string.digits, k=20))

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

        res = self.master_group.find_one({"admin_id": update.effective_user.id})
        if not res:
            res = {"admin_id": update.effective_user.id}
            self.master_group.insert_one(res)
        else:
            if 'link_msg_id' in res:
                msg_id = res['link_msg_id']
                chat_id = update.effective_chat.id
                bot.edit_message_text("Please use new message", chat_id=chat_id, message_id=msg_id)

        text = self.WELCOMETEXT % (self.bot.name,
                                   update.effective_user.first_name,
                                   update.effective_user.last_name,
                                   res.get('admin_group_link', ''),
                                   res.get('other_group_link', ''))
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("Create Admin Group Link",
                                  callback_data="mgh cal %s" % (chat_user_id))],
            [InlineKeyboardButton("Create Other Group Link",
                                  callback_data="mgh col %s" % (chat_user_id))]])
        new_msg = update.message.reply_text(text, reply_markup=markup)

        res = self.master_group.update_one({"admin_id": update.effective_user.id},
                                           {"$set": {"link_msg_id": new_msg.message_id}})

    def group_link_handler(self, bot, update, groups):
        password = self._gen_password()
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        if groups[1:] != (str(chat_id), str(user_id)):
            update.callback_query.answer(
                text="Please use your own group links",
                show_allert=True)
            return

        if groups[0] == 'col':
            res = self.master_group.find_one_and_update({"admin_id": update.effective_user.id},
                                                        {"$set": {"other_group_link": password}},
                                                        return_document=ReturnDocument.AFTER)
        elif groups[0] == 'cal':
            res = self.master_group.find_one_and_update({"admin_id": update.effective_user.id},
                                                        {"$set": {"admin_group_link": password}},
                                                        return_document=ReturnDocument.AFTER)
        else:
            update.callback_query.message.reply_text("Something went wrong in group_link_handler", quote=False)
        if not res:
            update.callback_query.message.reply_text("No master_group found for group.", quote=False)
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

    def admin_group_link_handler(self, bot, update, groups):
        pass
