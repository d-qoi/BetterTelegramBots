import logging
import argparse
import sys

from telegram import Bot
from telegram.ext import Dispatcher, CommandHandler
from telegram.error import InvalidToken

from sanic import Sanic

from queue import Queue

app = Sanic(__name__)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

URL = ""
PORT = 8443
PRIV = ""
PUB = ""
BOT_LIST = {}


def ping(bot, update):
    update.message.reply_text('pong')


def add_token(bot, update, args):
    logger.info("add_token: %s" % update.message)
    res = newEntery(args[0])
    if not res:
        logger.info("Not a valid token")
    update.message.reply_text("Added")
    logger.info("Added bot")


def newEntery(token):
    global BOT_LIST
    try:
        bot = Bot(token)
    except InvalidToken:
        return False

    update_queue = Queue()
    dp = Dispatcher(bot, update_queue, workers=1)

    dp.add_handler(CommandHandler('ping', ping))
    dp.add_handler(CommandHandler('add_token', add_token, pass_args=True))

    webhook_url = "%s/%s" % (URL, token)

    with open(PUB, 'rb') as cert:
        bot.set_webhook(url=webhook_url,
                        certificate=cert)

    BOT_LIST[token] = (dp, update_queue)
    return True


@app.route("/<token>", methods=["POST"])
async def webhook(request, token):
    logger.info("Webhook received")
    logger.info("Request: %s" % str(request))
    logger.info("Token: %s" % token)

if __name__ == '__main__':
    global BOT_LIST, URL, PORT, PRIV, PUB
    parser = argparse.ArgumentParser()
    parser.add_argument('auth', type=str, help="The Auth Token given by Telegram's @botfather")
    parser.add_argument('url', type=str, help="url that connects the bot to the rest of the world")
    parser.add_argument('port', type=int, help="port for the url", default=8443)
    parser.add_argument('priv', type=str, help="private key")
    parser.add_argument('pub', type=str, help="public key")
    res = newEntery(parser.auth)
    URL = parser.url
    PORT = parser.port
    PRIV = parser.priv
    PUB = parser.pub

    if res:
        BOT_LIST.append(res)
    else:
        logger.error("Invalid token")
        sys.exit(1)

    app.run(host=URL, port=PORT, ssl=PRIV, workers=5)
