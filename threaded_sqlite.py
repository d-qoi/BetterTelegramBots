import logging
from threading import Thread
from queue import Queue
import sqlite3

logger = logging.getLogger("__main__.ThreadedSqlite")


class ThreadedSqlite(Thread):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.reqs = Queue()
        self.start()

    def run(self):
        cnx = sqlite3.Connection(self.db)
        logger.info("Database connection opened")
        cursor = cnx.cursor()
        while True:
            req, arg, res = self.reqs.get()
            logger.debug("Running query: %s" % req)
            if arg:
                logger.debug("args: %s" % str(arg))
            try:
                if req == '--close--':
                    break
                elif req == '--commit--':
                    cnx.commit()
                    logger.info("Database commit")
                    continue
                elif req == '--last row id--':
                    if res:
                        res.put(cursor.lastrowid)
                        res.put('--no more--')
                    continue
                cursor.execute(req, arg)
                if res:
                    for rec in cursor:
                        res.put(rec)
                    res.put('--no more--')
            except sqlite3.OperationalError as e:
                logger.error("Error in execution")
                logger.error(str(e))
            logger.debug("Query Completed")
        cnx.close()
        logger.info("Database connection closed")

    def execute(self, req, arg=None, res=None):
        self.reqs.put((req, arg or tuple(), res))
        logger.debug("queue length: %d" % self.reqs.qsize())

    def select(self, req, arg=None):
        res = Queue()
        self.execute(req, arg, res)
        while True:
            rec = res.get()
            if rec == '--no more--': break
            yield rec

    def commit(self):
        self.execute("--commit--")

    def close(self):
        self.execute('--close--')

    def last_row_id(self):
        res = Queue()
        last_id = None
        self.execute('--last row id--', None, res)
        while True:
            rec = res.get()
            if rec == '--no more--':
                break
            else:
                last_id = rec
        return last_id
