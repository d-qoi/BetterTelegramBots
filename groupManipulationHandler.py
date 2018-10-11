import logging

from telegram.ext import MessageHandler
from telegram.ext.filters import Filters, BaseFilter

class GroupManipulationHandler(object):
    bot = None
    MDB = None
    DP = None

    master_group = None
    other_groups = None
    users = None
