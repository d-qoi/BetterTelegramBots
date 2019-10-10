import argparse
import logging

from telegram import TelegramError

from telegram.ext import CommandHandler, MessageHandler, Updater
from telegram.ext import PicklePersistence
from telegram.ext.filters import Filters

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger()

AUTHTOKEN = None
BANLIST = None


def check_if_admin(update, context):
    bot = context.bot
    bot_id = bot.id
    admins = bot.get_chat_administrators(update.effective_chat.id)
    for chatMember in admins:
        if chatMember.user.id == bot_id:
            return True
    return False


def auto_ban(update, context):
    if not check_if_admin(update, context):
        update.message.reply_text("Please make me an admin to preform this function.", quote=False)
        return

    chat_id = update.effective_chat.id
    job = context.job_queue.get_jobs_by_name(str(chat_id))
    if job:
        update.message.reply_text("""Job is already running. 
If you want it to run more frequently update /autobanfrequency""",
                                  quote=False)
        return

    context.job_queue.run_repeating(update_auto_ban_list_job,
                                    context.chat_data.get("interval", 3600),
                                    first=0,
                                    context=chat_id,
                                    name=str(chat_id))
    context.chat_data["Job Started"] = True
    update.message.reply_text("Starting the auto ban process, may take a moment.", quote=False)


def welcome_ban_list(update, context):
    new_members = update.message.new_chat_member
    for chatMember in new_members:
        if chatMember.id in BANLIST:
            if check_if_admin(update, context):
                context.bot.kick_chat_member(update.effective_chat.id, update.effective_user.id)
            else:
                admins = context.bot.get_chat_administrators(update.effective_chat.id)
                names = ""
                for admin in admins:
                    if admin.user.username:
                        names += " @" + chatMember.user.username
                update.message.reply_text(names + "\n\n the person that just joined is on the ban list.")


def update_auto_ban_list_job(context):
    for id in BANLIST:
        try:
            chatMember = context.bot.get_chat_member(context.)
        except TelegramError:
            pass


def update_ban_list_freq(update, context):
    pass


def message_handler(update, context):
    if context.chat_data["Job Started"]:
        chat_id = update.effective_chat.id
        job = context.job_queue.get_jobs_by_name(str(chat_id))
        if job:
            return
        context.job_queue.run_repeating(update_auto_ban_list_job,
                                        context.chat_data.get("interval", 3600),
                                        first=0,
                                        context=chat_id,
                                        name=str(chat_id))



def add_uid_to_list(update, context):
    pass

def main():
    pp = PicklePersistence("session.pickle")
    updater = Updater(AUTHTOKEN, use_context=True, persistence=pp)
    dp = updater.dispatcher

    dp.add_handler(MessageHandler(Filters.status_update.new_chat_members,
                                  welcome_ban_list,
                                  pass_chat_data=True))

    dp.add_handler(CommandHandler("autoban", auto_ban, Filters.group, pass_job_queue=True))
    dp.add_handler(CommandHandler("autobanfrequency", update_ban_list_freq, Filters.group, pass_job_queue=True))

    dp.add_handler(CommandHandler("ytk_add_uid", add_uid_to_list, Filters.private))

    dp.add_handler(MessageHandler(Filters.group, message_handler, pass_chat_data=True, pass_job_queue=True))






if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('auth', type=str, help="The Auth Token given by Telegram's @botfather")
    parser.add_argument('-l', '--llevel', default='info', choices=['debug', 'info', 'warn', 'none'],
                        help='Logging level for the logger, default = info')
    parser.add_argument("-b", "--banlist", type=argparse.FileType("rw"),
                        help="new line separated list of user IDs")
    logLevel = {'none': logging.NOTSET, 'debug': logging.DEBUG, 'info': logging.INFO, 'warn': logging.WARNING}
    args = parser.parse_args()

    logger.setLevel(logLevel[args.llevel])
    AUTHTOKEN = args.auth
    BANLIST = parser.banlist
    uids = []
    with open(BANLIST, "r") as bl:
        for line in bl:
            uids.append(int(line))
    BANLIST = uids

    main()
