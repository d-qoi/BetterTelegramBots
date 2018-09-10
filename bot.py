import argparse
import logging
from pymongo import MongoClient
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, TelegramError
from telegram.ext import Updater, CommandHandler, Filters, MessageHandler, CallbackQueryHandler, Job

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)',
                    level=logging.INFO)
logger = logging.getLogger(__name__)


# Globals
AUTHTOKEN = None
MCLIENT = None
MDB = None
INFOTEXT = None
WELCOMETEXT = None

def start():
    pass

def info():
    pass

def start_from_cli():
    pass

def main():
    try:
        serverInfo = MCLIENT.server_info()
        logger.info("Connected to Mongo Server.")
        logger.debug("Mongo Server info: %s." % serverInfo)
    except:
        logger.error("Could not connect to the Mongo Server.")
        raise
    updater = Updater(AUTHTOKEN)

    dp = updater.dispatcher

def startFromCLI():
    global AUTHTOKEN, MCLIENT, MDB, INFOTEXT, WELCOMETEXT
    parser = argparse.ArgumentParser()
    parser.add_argument('auth', type=str, help="The Auth Token given by Telegram's @botfather")
    parser.add_argument('-l','--llevel', default='info', choices=['debug','info','warn','none'], help='Logging level for the logger, default = info')
    logLevel = {'none':logging.NOTSET,'debug':logging.DEBUG,'info':logging.INFO,'warn':logging.WARNING}
    parser.add_argument('-muri','--MongoURI', default='mongodb://localhost:27017', help="The MongoDB URI for connection and auth")
    parser.add_argument('-mdb','--MongoDB', default='feedbackbot', help="The MongoDB Database that this will use")
    parser.add_argument('-i','--InfoText',default=" ", help='A "quoted" string containing a bit of text that will be displayed when /info is called')
    parser.add_argument('-w','--WelcomeText', default = 'Welcome! Please PM this bot to give feedback.', help='A "quoted" string containing a bit of text that will be displayed when a user joins.')
    args = parser.parse_args()

    logger.setLevel(logLevel[args.llevel])
    AUTHTOKEN = args.auth
    MCLIENT = MongoClient(args.MongoURI)
    MDB = MCLIENT[args.MongoDB]
    INFOTEXT = args.InfoText # + "\n\nBot created by @YTKileroy"
    WELCOMETEXT = args.WelcomeText

if __name__ == "__main__":
    startFromCLI()
    main()
