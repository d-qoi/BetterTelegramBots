import logging
import sqlite3
import sys

from sql_queries import *
from pyrogram import Client, Filters

logger = logging.getLogger("root")
sf = logging.StreamHandler(sys.stdout).setFormatter(
    logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
)
logger.addHandler(sf)
logger.setLevel(logging.INFO)

connection = sqlite3.connect("data/messages.db")
cursor = connection.cursor()
cursor.executescript('\n'.join([
    CREATE_TABLE_USER,
    CREATE_TABLE_MESSAGE,
    CREATE_TABLE_TEXT_MESSAGE,
    CREATE_TABLE_FORWARDED_MESSAGE,
]))



