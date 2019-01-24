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
    """
    This filter probably should not exist in this state

    This filter is desigend to take care of adding a group as
    either an admin group or other group.

    Not entirely sure why I thought it was a good idea to do this work
    in a filter, but it should work just fine.

    It will cause a lot of requests to hit Mongo all at once, but it shouldn't
    matter with the number of people who will be using this bot.

    Joining both of the checks and additions here will make it possible
    to seperate out the adminGroupHandler and the otherGroupHandler.
    """
    name = "Group Add Check Filter"
    pattern = re.compile("^[" + string.digits + string.ascii_letters + "]+$")

    admin_group = None
    group_config = None

    logger = logging.getLogger(__name__)

    ADMIN_GROUP = 0
    OTHER_GROUP = 1

    def __init__(self, master_group, group_config, group_type):
        self.logger.debug("Initializing")
        self.admin_group = master_group
        self.group_config = group_config
        self.group_type = group_type

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
        if self.admin_group.find_one({"group_id": message.chat.id,
                                      "admin_id": message.from_user.id}):
            return False

        self.logger.debug("New Potential Group")
        res = self.admin_group.find_one({"$or":
                                          [{"admin_group_link": text},
                                           {"other_group_link": text}],
                                          "admin_id": message.from_user.id})
        if not res:
            return False

        self.logger.info("New Group Added: %s" % str(res))
        self.logger.debug("New Group Chat: %s" % str(message.chat))

        if res.get("other_group_link") == text and self.group_type is self.OTHER_GROUP:
            gd = {
                "group_id": message.chat.id,
                "group_title": message.chat.title,
                "master_group": res["_id"]
            }
            gd = self.group_config.insert_one(gd)
            self.logger.debug("New Other Group: %s" % str(gd))
            return True

        elif res.get('admin_group_link') == text and self.group_type is self.ADMIN_GROUP:
            self.logger.debug("New Admin Group")
            res = self.admin_group.update_one(
                {"admin_group_link": text},
                {"$set": {"group_id": message.chat.id}})
            return True

        else:
            self.logger.error("Error in mongoDB lookup or no group with given link")
            return False


class CheckAdminGroup(BaseFilter):
    name = "Check Admin Group"

    admin_group = None
    logger = logging.getLogger(__name__)
    cache = {}

    def __init__(self, master_group):
        self.logger.debug("Initializing")
        self.admin_group = master_group

    def check_cache(self, group_id):
        self.logger.debug("checking cache for %d", group_id)
        if group_id in self.cache:
            self.logger.debug("cache hit")
            return self.cache[group_id]
        self.cache[group_id] = bool(self.admin_group.find_one({"group_id": group_id}))
        self.logger.debug("cache miss")
        return self.cache[group_id]

    def clear_cache(self):
        self.logger.warn("Check Admin Group cache cleared")
        self.cache.clear()

    def update_cache_for(self, group_id):
        self.logger.info("Check admin group cache cleared for %d" % group_id)
        self.cache.pop(group_id, None)

    def filter(self, message):
        self.logger.debug("CheckAdminGroup filter check")
        return self.check_cache(message.chat.id)


class CheckOtherGroup(BaseFilter):
    name = "Check Other Group"

    group_config = None
    logger = logging.getLogger(__name__)

    def __init__(self, group_config):
        self.logger.debug("Initializing")
        self.group_config = group_config

    def check_cache(self, group_id):
        self.logger.debug("checking cache for %d", group_id)
        if group_id in self.cache:
            self.logger.debug("cache hit")
            return self.cache[group_id]
        self.cache[group_id] = bool(self.group_config.find_one({"group_id": group_id}))
        self.logger.debug("cache miss")
        return self.cache[group_id]

    def clear_cache(self):
        self.logger.warn("Check Other Group cache cleared")
        self.cache.clear()

    def update_cache_for(self, group_id):
        self.logger.info("Check Other group cache cleared for %d" % group_id)
        self.cache.pop(group_id, None)

    def filter(self, message):
        self.logger.debug("CheckOtherGroup filter check")
        return self.check_cache(message.chat.id)
