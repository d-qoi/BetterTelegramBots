import argparse
import logging
from pymongo import MongoClient, DESCENDING
import time
import re
from uuid import uuid4

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

from telegram import InlineKeyboardMarkup, InlineKeyboardButton, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import Updater, InlineQueryHandler, ChosenInlineResultHandler, CommandHandler, MessageHandler, \
    CallbackQueryHandler

from telegram.ext.filters import  Filters

AUTHTOKEN = ""
MDB = None
MCLIENT = None

MENU_CLOSE = 'm0'
MENU_CREATE = 'm1'
MENU_DELETE = 'm2'
MENU_UPDATE = 'm3'
MENU_LINK = 'm4'
MENU_START = "menu start"
MENU_YES = "m5"
MENU_NO = "m6"


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
                                                         "state": MENU_START,
                                                         "active_user": user_id}},
                         upsert=True)


def setupMenuCallbackHandler(bot, update):
    logger.debug("Menu Callback Hit")
    query = update.callback_query
    data = query.data
    logger.debug("Data: %s" % data)
    chat_id = query.message.chat.id
    message_id = query.message.message_id
    user_id = query.from_user.id

    state = MDB.state.find_one({"chat_id": chat_id})
    if not state:
        query.answer("This is not in the correct chat.")
        logger.warning("State not found for chat %d, returning" % chat_id)
        return

    if isAdminOfChat(bot, chat_id, user_id):
        logger.debug("is admin of chat, checking setup modes")

        if state["state"] == MENU_START:
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
                num_gates = MDB.gates.count_documents({"chat_id": chat_id})

                if num_gates >= 10:
                    bot.edit_message_text(
                        "You can only have 10 gateways, please delete one if you want to make a new one.",
                        chat_id=chat_id, message_id=message_id)
                    query.answer("You have reached your gateway limit")
                    return

                bot.edit_message_text(
                    "Please send me the name of the new gateway (not inline)",
                    chat_id=chat_id, message_id=message_id)
                MDB.state.update_one({"chat_id": chat_id},
                                     {"$set": {"state": MENU_CREATE,
                                               "active_user": user_id}})

                return

            elif data == MENU_UPDATE:
                gateways = MDB.gates.find({"chat_id": chat_id})
                if gateways is None:
                    query.anser("Please create a gateway first")
                    return
                gateways = gateways.sort("text", DESCENDING)

                keyboard = []
                for gate in gateways:
                    keyboard.append([InlineKeyboardButton(gate.text, callback_data="m%d" % gate.time)])
                markup = InlineKeyboardMarkup(keyboard)

                query.answer("Please select the gate")
                bot.edit_message_text(
                    "Please choose the gateway you would like to edit",
                    chat_id=chat_id, message_id=message_id, reply_markup=markup)

                MDB.state.update_one({"chat_id": chat_id},
                                     {"$set": {"state": MENU_UPDATE,
                                               "active_user": user_id}})

                return

            elif data == MENU_DELETE:
                gateways = MDB.gates.find({"chat_id": chat_id})
                if gateways is None:
                    query.anser("Please create a gateway first")
                    return
                gateways = gateways.sort("text", DESCENDING)

                keyboard = []
                for gate in gateways:
                    keyboard.append([InlineKeyboardButton(gate.text, callback_data="m%d" % gate.time)])
                markup = InlineKeyboardMarkup(keyboard)

                query.answer("Please select the gate")
                bot.edit_message_text(
                    "Please choose the gateway you would like to delete",
                    chat_id=chat_id, message_id=message_id, reply_markup=markup)

                MDB.state.update_one({"chat_id": chat_id},
                                     {"$set": {"state": MENU_DELETE,
                                               "active_user": user_id}})
                return

        elif state['state'] == MENU_UPDATE and state['active_user'] == user_id:
            ctime = int(data[1:])
            gate = MDB.gates.find_one({"chat_id": chat_id, "time": ctime})
            if not gate:
                logger.error("Gate selected does not exist for update, returning")
                query.answer("An error occurred, please try again.")
                bot.edit_message_text("The gate you selected does not exist. If this persists, talk to @ytkileroy",
                                      chat_id=chat_id, message_id=message_id, reply_markup=None)
                return
            query.answer("Found gate, preparing to update")
            keyboard = [[
                InlineKeyboardButton("To Inline Mode",
                                     switch_inline_query_current_chat=" ")
            ]]
            markup = InlineKeyboardMarkup(keyboard)
            bot.edit_message_text("""
Please send the bot a @username or https://t.me/... link via an inline query.
The query results will update to say it found a username or link. 
After you have completed typing, click on the query response to alert the bot that you are done.
Feel free to delete the message you send via the bot after you are done with the inline bot.""",
                                  chat_id=chat_id, message_id=message_id, reply_markup=markup)
            MDB.state.update_one({"chat_id": chat_id},
                                 {"$set": {
                                     "state": MENU_LINK,
                                     "active_gate": gate["_id"]
                                 }})
            return
        elif state['state'] == MENU_DELETE and state['active_user'] == user_id:
            if data == MENU_NO:
                query.answer("Not deleting gateway")
                bot.edit_message_text("Gateway not deleted, please send /setup to continue",
                                      chat_id=chat_id, message_id=message_id, reply_markup=None)
                return
            elif data == MENU_YES:
                query.answer("Deleting gateway")
                bot.edit_message_text("Gateway deleted, please send /setup to continue",
                                      chat_id=chat_id, message_id=message_id, reply_markup=None)
                return
            ctime = int(data[1:])
            gate = MDB.gates.find_one({"chat_id": chat_id, "time": ctime})
            if not gate:
                logger.error("Gate selected does not exist for deleting, returning")
                query.answer("An error occurred, please try again.")
                bot.edit_message_text("The gate you selected does not exist. If this persists, talk to @ytkileroy",
                                      chat_id=chat_id, message_id=message_id, reply_markup=None)
                return
            query.answer("Found gate, preparing to delete")
            keyboard = [
                [InlineKeyboardButton("Yes", callback_data=MENU_YES)],
                [InlineKeyboardButton("No", callback_data=MENU_NO)]
            ]
            markup = InlineKeyboardMarkup(keyboard)
            bot.edit_message_text("Are you sure you want to delete gateway: %s" % gate.title,
                                  chat_id=chat_id, message_id=message_id, reply_markup=markup)
            MDB.state.update_one({"chat_id": chat_id},
                                 {"$set": {"active_gate": gate["_id"]}})


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
        logger.debug("State not found, returning")
        return
    if state['state'] != MENU_CREATE:
        logger.debug("Not in MENU_CREATE state, returning")
        return

    if len(text) > 100:
        logger.debug("Message too long, returning")
        update.message.reply_text("Please keep the gateway title to under 100 characters. This message is %d characters" % len(text))
        return

    logger.debug("Passed checks")

    MDB.gates.insert_one({"chat_id": chat_id, "text": text, "link": None, "time": int(time.time())})
    update.message.reply_text("Gateway Created. Please update the gateway link via the config menu.")
    setupMenu(bot, update)


def createGateway(bot, update):
    logger.debug("MenuTextHandler called")
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if not isAdminOfChat(bot, chat_id, user_id):
        logger.debug("Non admin called, returning")
        return

    gateways = MDB.gates.find({"chat_id": chat_id})
    if not gateways:
        update.message.reply_text("Please /setup a few gateways first!", quote=False)
        return

    keyboard = []
    for gate in gateways:
        keyboard.append([InlineKeyboardButton(text=gate.title, callback_data=str(gate.time))])

    if not keyboard:
        update.message.reply_text("Create a few Gateways first with /setup",
                                  quote=False)
        return

    markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text("Gateways for %s" % update.effective_chat.title,
                              reply_markup=markup, quote=False)


def gatewayCallbackHandler(bot, update):
    logger.debug("gateway callback handler called")
    query = update.callback_query
    data = int(query.data)
    logger.debug("Data: %s" % data)
    chat_id = query.message.chat.id
    user_id = query.from_user.id

    gate = MDB.gates.find_one({"chat_id": chat_id, "time": data})
    if gate and gate.link is not None:
        query.answer(url=gate['link'])
        return
    query.answer("No link found")


def helpMessage(bot, update):
    pass


username_pattern = re.compile("@(\w{5,})")
link_pattern = re.compile("https://t\.me/(joinchat/)?\w{5,}")


def inlineQuery(bot, update):
    logger.debug("Inline Querry called")

    query = update.inline_query.query
    user_id = update.inline_query.from_user.id

    if username_pattern.fullmatch(query):
        result = [
            InlineQueryResultArticle(
                id=uuid4(),
                title="Username, click here to complete",
                input_message_content=InputTextMessageContent("Username saved")
            )
        ]
    elif link_pattern.fullmatch(query):
        result = [
            InlineQueryResultArticle(
                id=uuid4(),
                title="Link, click here to complete",
                input_message_content=InputTextMessageContent("Link saved")
            )
        ]
    else:
        result = [
            InlineQueryResultArticle(
                id=uuid4(),
                title="Please send a @username",
                input_message_content=InputTextMessageContent("Please send a @username")
            ),
            InlineQueryResultArticle(
                id=uuid4(),
                title="or a https://t.me/... link",
                input_message_content=InputTextMessageContent("Or a https://t.me/... link")
            )
        ]

    update.inline_query.answer(result)
    logger.debug(str(update))


def chosenInlineQuery(bot, update):
    logger.debug("Inline Query Response")
    logger.info(str(update))
    query = update.chosen_inline_result.query
    user_id = update.chosen_inline_result.from_user.id
    if username_pattern.fullmatch(query):
        username = username_pattern.fullmatch(query).group(1)
        link = "https://t.me/%s" % username
    elif link_pattern.fullmatch(query):
        link = query
    else:
        logger.warning("Unknown chosen_inline_result: %s" % query)
        return

    res = MDB.state.find_one({"state": MENU_LINK,
                              "active_user": user_id})
    MDB.gates.update_one({"_id": res['_id']},
                         {"$set": {
                             "link": link
                         }})
    bot.delete_message(chat_id=res['chat_id'], message_id=res['msg_id'])
    MDB.state.delete_one({"chat_id": res['chat_id']})


def main():
    updater = Updater(AUTHTOKEN)

    dp = updater.dispatcher

    dp.add_handler(InlineQueryHandler(inlineQuery))
    dp.add_handler(ChosenInlineResultHandler(chosenInlineQuery))
    dp.add_handler(CallbackQueryHandler(setupMenuCallbackHandler, pattern="m\d+"))
    dp.add_handler(CallbackQueryHandler(gatewayCallbackHandler, pattern="\d+"))
    dp.add_handler(CommandHandler("create_gateway", createGateway, filters=Filters.group))
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
