import logging
import argparse

from telegram import Bot, Update
from telegram.ext import Updater, MessageHandler, Job
from telegram.ext.filters import Filters
from telegram.error import InvalidToken

welcome_message = """Welcome to the chat!

Please talk to one of the admins within two hours if you would like to interact with this chat.
"""

def kick_member(bot, job):
    bot.kick_chat_member(job.context['chat'],
                         job.context['user'],
                         until_date=0)


def newMemberHandler(bot, update, job_queue=None):
    new_members = update.message.new_chat_member
    for member in new_members:
        bot.restrict_chat_member(update.effective_chat.id,
                                 member.id,
                                 can_send_message=False,
                                 can_send_media_messages=False,
                                 can_send_other_messages=False,
                                 can_add_web_page_previews=False)
        to_kick = job_queue.run_once(kick_member,
                                     context={"chat": update.effective_chat.id,
                                              "user": member.id},
                                     when=60*60*2,  # two hours
                                     name="%d" % member.id)

    update.message.reply_text(welcome_message, quote=False)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('auth', type=str,
                        help="The Auth Token given by Telegram's @botfather")
    args = parser.parse_args()
    auth = args.auth

    updater = Updater(auth)
    dp = updater.dp

    dp.add_handler(MessageHandler(Filters.status_update.new_chat_member,
                                  newMemberHandler), pass_job_queue=True)

    updater.start_polling()
    updater.idle()
