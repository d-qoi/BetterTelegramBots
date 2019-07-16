import logging

from sql_queries import *
from tel_client import TelClient
from threaded_sqlite import ThreadedSqlite

logging.basicConfig(level=logging.WARNING,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M')

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

sql = ThreadedSqlite("data/messages.db")


sql.execute(CREATE_TABLE_USER)
sql.execute(CREATE_TABLE_MESSAGE)
sql.execute(CREATE_TABLE_TEXT_MESSAGE)
sql.execute(CREATE_TABLE_LOCATION)
sql.execute(CREATE_TABLE_CONTACT_MESSAGE)
sql.execute(CREATE_TABLE_FILE_MESSAGE)
sql.execute(CREATE_TABLE_OTHER_MESSAGE)
sql.execute(CREATE_TABLE_VENUE)
sql.execute(INSERT_USER, (-1, "DELETED", "DELETED", "ACCOUNT"))
logger.debug("Last Row ID: %d" % sql.last_row_id())


logger.info("Starting")
logger.debug("Starting")

telclient = TelClient(sql)
telclient.app.run()

sql.commit()
sql.close()
