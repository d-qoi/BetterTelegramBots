import logging
import re
import string

from telegram import Chat
from telegram.ext.filters import BaseFilter


class MGFilter(BaseFilter):
    name = "master_group_filter"
    group_id = None
    global_config = None

    logger = logging.getLogger(__name__)

    def __init__(self, global_config):
        self.logger.debug("Initializing")
        self.global_config = global_config
        self._update_cache()

    def _update_cache(self):
        if not self.group_id:
            self.logger.debug("Ampting to update cache")
            res = self.global_config.find_one()
            if res:
                self.group_id = res['group']
                self.logger.debug("Cache Updated: %d" % self.group_id)

    def filter(self, message):
        self.logger.debug("Filtering message: %s" % str(message))
        self._update_cache()
        return message.chat.id == self.group_id


class GroupAddCheckFilter(BaseFilter):
    name = "Group Add Check Filter"
    pattern = re.compile("^[" + string.digits + string.ascii_letters + "]+$")

    master_group = None
    group_config = None

    def __init__(self, master_group, group_config):
        self.logger.debug("Initializing")
        self.master_group = master_group
        self.group_config = group_config

    def filter(self, message):
        text = message.text
        if message.chat.type not in [Chat.GROUP, Chat.SUPERGROUP]:
            return False
        if len(text) != 20:
            return False
        if not self.pattern.match(text):
            return False
        if self.group_config.find_one({"group_id": message.chat.id}):
            return False
        if self.master_group.find_one({"group_id": message.chat.id}):
            return False

        self.logger.debug("New Potential Group")
        res = self.master_group.find_one({"$or":
                                          [{"admin_group_link": text},
                                           {"other_group_link": text}]})
        if not res:
            return False

        self.logger.info("New Group Added: %s" % str(res))
        self.logger.debug("New Group Chat: %s" % str(message.chat))

        if res["other_group_link"] == text:
            gd = {
                "group_id": message.chat.id,
                "group_title": message.chat.title,
                "master_group": res["_id"]
            }
            gd = self.group_config.insert_one(gd)
            self.logger.debug("New Other Group: %s" % str(gd))
            return True

        elif res['admin_group_link'] == text:
            self.logger.debug("New Admin Group")
            res = self.master_group.update_one(
                {"admin_group_link": text},
                {"$set": {"group_id": message.chat.id}})
            return True

        else:
            self.logger.error("Error in mongoDB lookup")
            return False
