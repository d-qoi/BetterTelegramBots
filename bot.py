import argparse
import logging
from pymongo import MongoClient, DESCENDING

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

from telegram import InlineKeyboardMarkup, InlineKeyboardButton, InlineQuery, InlineQueryResult
from telegram.ext import Updater, InlineQueryHandler, CommandHandler, MessageHandler
from telegram.ext.filters import  Filters

AUTHTOKEN = ""
MDB = None
MCLIENT = None

MENU_CLOSE = '-1'
MENU_CREATE = '1'
MENU_DELETE = '2'
MENU_UPDATE = '3'
MENU_START = "menu start"


def isAdminOfChat(bot, chat_id, user_id):
    logger.debug("isAdminOfChat called for %d %d" % (chat_id, user_id))

    res = bot.get_chat_administrators(chat_id)

    logger.debug("%d admins" % len(res))

    for cm in res:
        if cm.user.id == user_id:
            return True

    return False


def setupMenu(bot, update):
    logger.debug("setupMenu called")

    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if not isAdminOfChat(bot, chat_id, user_id):
        logger.debug("Non admin called, returning")
        return
    logger.info("Admin called setupMenu for %s (%d)" % (update.effective_chat.title, chat_id))

    menu = [
        [InlineKeyboardButton("Create Gate", callback_data=MENU_CREATE)],
        [InlineKeyboardButton("Edit Gate", callback_data=MENU_UPDATE)],
        [InlineKeyboardButton("Delete Gate", callback_data=MENU_DELETE)],
        [InlineKeyboardButton("Close", callback_data=MENU_CLOSE)]
    ]

    keyboard = InlineKeyboardMarkup(menu)

    mdb_prev_message = MDB.state.find_one({"chat_id": chat_id})
    if mdb_prev_message is not None:
        logger.debug("removing old message")
        bot.delete_message(chat_id, mdb_prev_message.msg_id)
        MDB.state.delete_one({"chat_id": chat_id})

    new_message = bot.sendMessage(chat_id, "Gateway config menu for %s" % update.effective_chat.title, reply_markup=keyboard)

    MDB.state.update_one({"chat_id": chat_id}, {"$set": {"msg_id": new_message.message_id,
                                                         "state": MENU_START}},
                         upsert=True)


def setupMenuCallbackHandler(bot, update):
    logger.debug("Menu Callback Hit")
    query = update.callback_query
    data = query.data
    logger.debug("Data: %s" % data)
    chat_id = query.message.chat.id
    message_id = query.message.message_id
    user_id = query.from_user.id

    if not isAdminOfChat(bot, chat_id, user_id):
        logger.debug("Is not admin of chat, returning")
        query.answer("You are not an admin")
        return

    if data == MENU_CLOSE:
        mdb_prev_message = MDB.state.find_one({"chat_id": chat_id})
        if mdb_prev_message is not None:
            query.answer("Closing Menu")
            bot.delete_message(chat_id, message_id)
            MDB.state.delete_one({"chat_id": chat_id})
        else:
            logger.warning("Delete error for %d" % chat_id)
            query.answer("Something went wrong, closing anyway")
            bot.delete_message(chat_id, message_id)
        return

    elif data == MENU_CREATE:
        query.anser("Creating new Gateway")
        bot.edit_message_text(
            "Please send me the name of the new gateway (not inline)",
            chat_id=chat_id, message_id=message_id)
        MDB.state.update_one({"chat_id": chat_id},
                             {"$set": {"state": MENU_CREATE}})
        return

    elif data == MENU_UPDATE:
        gateways = MDB.gates.find({"chat_id": chat_id})
        if gateways is None:
            query.anser("Please create a gateway first")
            return
        gateways = gateways.sort("text", DESCENDING)

        keyboard = []
        for gate in gateways:
            keyboard.append(InlineKeyboardButton(gate.text, callback_data=gate.id))
        markup = InlineKeyboardMarkup(keyboard)

        query.answer("Please select the gate")
        bot.edit_message_text(
            "Please choose the gateway you would like to edit",
            chat_id=chat_id, message_id=message_id, reply_markup=markup)

        MDB.state.update_one({"chat_id": chat_id},
                             {"$set": {"state": MENU_UPDATE}})

        return

    elif data == MENU_DELETE:
        gateways = MDB.gates.find({"chat_id": chat_id})
        if gateways is None:
            query.anser("Please create a gateway first")
            return
        gateways = gateways.sort("text", DESCENDING)

        keyboard = []
        for gate in gateways:
            keyboard.append(InlineKeyboardButton(gate.text, callback_data=gate.id))
        markup = InlineKeyboardMarkup(keyboard)

        query.answer("Please select the gate")
        bot.edit_message_text(
            "Please choose the gateway you would like to delete",
            chat_id=chat_id, message_id=message_id, reply_markup=markup)

        MDB.state.update_one({"chat_id": chat_id},
                             {"$set": {"state": MENU_DELETE}})
        return


def setupMenuTextHandler(bot, update):
    logger.debug("MenuTextHandler called")
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    text = update.message.text

    if not isAdminOfChat(bot, chat_id, user_id):
        logger.debug("Non admin called, returning")
        return

    state = MDB.state.find_one({"chat_id": chat_id})
    if not state:
        return
    if state.state != MENU_CREATE:
        return

    logger.debug("Passed checks")
    gates = MDB.gates.find({"chat_id": chat_id})
    if gates:
        number

def createGatewayMenu(bot, update):
    pass


def helpMessage(bot, update):
    pass

def inlineQuery(bot, update):
    pass


def main():
    updater = Updater(AUTHTOKEN)

    dp = updater.dispatcher

    dp.add_handler(InlineQueryHandler(inlineQuery))
    dp.add_handler(CommandHandler("create_gateway", createGatewayMenu, filters=Filters.group))
    dp.add_handler(CommandHandler("setup", setupMenu, filters=Filters.group))
    dp.add_handler(CommandHandler("help", helpMessage, filters=Filters.private))
    dp.add_handler(MessageHandler(Filters.text, setupMenuTextHandler))

    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('auth', type=str, help="The Auth Token given by Telegram's @botfather")
    parser.add_argument('-l', '--llevel', default='info', choices=['debug', 'info', 'warn', 'none'],
                        help='Logging level for the logger, default = info')
    logLevel = {'none': logging.NOTSET, 'debug': logging.DEBUG, 'info': logging.INFO, 'warn': logging.WARNING}
    parser.add_argument('-muri', '--MongoURI', default='mongodb://localhost:27017',
                        help="The MongoDB URI for connection and auth")
    parser.add_argument('-mdb', '--MongoDB', default='gatewaybot', help="The MongoDB Database that this will use")
    args = parser.parse_args()

    logger.setLevel(logLevel[args.llevel])
    AUTHTOKEN = args.auth
    MCLIENT = MongoClient(args.MongoURI)
    MDB = MCLIENT[args.MongoDB]

    main()
