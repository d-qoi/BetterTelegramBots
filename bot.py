import logging
import argparse
import sys
import ujson

from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler
from telegram.error import InvalidToken

from flask import Flask
from flask_restful import Resource, Api

from queue import Queue

app = Flask(__name__)
api = Api(app)
#app.config.KEEP_ALIVE = False

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
    dp.start()

    logger.info("bot info")
    logger.info("webhook: %s" % str(bot.get_webhook_info()))
    logger.info("bot info: %s" % str(bot.get_me()))
    return True

@app.route("/")
def test(request):
    return response.json({"test": "test"})


@app.route("/<token>", method=["POST"])
def webhook(token):
    logger.info("Webhook received")
    if token not in BOT_LIST:
        raise Forbidden()
    logger.info("Request: %s" % str(request))
    logger.info("Request Json: %s" % str(request.json))
    logger.info("Token: %s" % token)

    logger.info("bot status: %s" % str(BOT_LIST[token][0].bot.get_webhook_info()))

    #BOT_LIST[token][1].put(Update.de_json(request.json, BOT_LIST[token][0]))
    #return response.text("OK")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('auth', type=str, help="The Auth Token given by Telegram's @botfather")
    parser.add_argument('url', type=str, help="url that connects the bot to the rest of the world")
    parser.add_argument('port', type=int, help="port for the url", default=8443)
    parser.add_argument('priv', type=str, help="private key")
    parser.add_argument('pub', type=str, help="public key")
    args = parser.parse_args()
    URL = args.url
    PORT = args.port
    PRIV = args.priv
    PUB = args.pub

    res = newEntery(args.auth)
    if not res:
        logger.error("Invalid token")
        sys.exit(1)

    ssl = (PUB, PRIV)
    app.run(host='0.0.0.0', port=PORT, ssl_context=ssl)
