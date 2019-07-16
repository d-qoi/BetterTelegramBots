import logging

from pyrogram import Client, Filters, MessageHandler, DeletedMessagesHandler
from pyrogram.api import functions, types
from pyrogram.errors import RPCError


from sql_queries import *

logger = logging.getLogger("__main__.tel_client")
logger.setLevel(logging.DEBUG)


class TelClient:
    def __init__(self, sql, client_name='tel_client_data'):
        self.app = Client(client_name)
        self.sql = sql

        self.app.add_handler(MessageHandler(self.private_message_handler, Filters.private))
        self.app.add_handler(DeletedMessagesHandler(self.deleted_message_handler))

    def private_message_handler(self, client, message):
        logger.info("Message Received")
        logger.debug("%s" % str(message))

        chat_id = message.chat.id
        message_id = message.message_id
        received_date = message.date
        if message.empty:
            self.sql.execute(INSERT_MESSAGE, (chat_id,message_id,-1, 0, 0,received_date,"deleted", "text"))
            return

        reply_to_message_id = 0
        if message.reply_to_message:
            reply_to_message_id = message.reply_to_message.message_id
            logger.debug("Reply_to_msg_id %d" % reply_to_message_id)
            output = []
            for value in self.sql.select(SELECT_MESSAGE_BY_ID, (reply_to_message_id, )):
                output.append(value)
            logger.debug("reply_to_message_check: %s" % str(output))
            if not output:
                logger.debug("message not found, creating new message")
                try:
                    message_replied = self.app.get_messages(chat_id, message_ids=reply_to_message_id)
                    logger.debug("able to get message, using retrieved message")
                    self.private_message_handler(client, message_replied)
                except RPCError as e:
                    logger.error("Unable to get message, using message from update")
                    self.private_message_handler(client, message.reply_to_message)

        from_user_id = message.from_user.id
        from_user_first_name = message.from_user.first_name
        from_user_last_name = message.from_user.last_name
        from_user_username = message.from_user.username
        received_date = message.date

        state = "new"
        if message.edit_date:
            state = "edited"
            received_date = message.edit_date

        forwarded_user_id = 0
        if message.forward_from:
            forwarded_user_id = message.forward_from.id
            forwarded_user_first_name = message.forward_from.first_name
            forwarded_user_last_name = message.forward_from.last_name
            forwarded_username = message.forward_from.username

            self.sql.execute(INSERT_USER, (forwarded_user_id,
                                           forwarded_username,
                                           forwarded_user_first_name,
                                           forwarded_user_last_name))

        self.sql.execute(INSERT_USER, (from_user_id,
                                       from_user_username,
                                       from_user_first_name,
                                       from_user_last_name))

        message_type = "text"
        if message.media:
            if message.audio:
                message_type = "audio"
            elif message.document:
                message_type = "document"
            elif message.photo:
                message_type = "photo"
            elif message.sticker:
                message_type = "sticker"
            elif message.video:
                message_type = "video"
            elif message.voice:
                message_type = "voice"
            elif message.video_note:
                message_type = "video_note"
            elif message.contact:
                message_type = "contact"
            elif message.location:
                message_type = "location"
            elif message.venue:
                message_type = "venue"
        logger.info("Message Type: %s" % message_type)
        self.sql.execute(INSERT_MESSAGE, (chat_id,
                                          message_id,
                                          from_user_id,
                                          forwarded_user_id,
                                          reply_to_message_id,
                                          received_date,
                                          state,
                                          message_type))

        if message_type == "text":
            self.sql.execute(INSERT_TEXT_MESSAGE, (message_id,
                                                   message.text.markdown))
        elif message_type == "audio":
            pass
        elif message_type == "document":
            pass
        elif message_type == "photo":
            pass
        elif message_type == "sticker":
            pass
        elif message_type == "video":
            pass
        elif message_type == "voice":
            pass
        elif message_type == "video_note":
            pass
        elif message_type == "contact":
            pass
        elif message_type == "location":
            pass
        elif message_type == "venue":
            pass


        self.sql.commit()


    def deleted_message_handler(self, client, message):
        logger.info("Deleted Message Received")
        logger.debug("%s" % str(message))


    def get_all_drafts(self):
        res = self.app.send(
            functions.messages.GetAllDrafts()
        )
        logger.debug(str(res))
        if isinstance(res, types.Update):
            for update in res.updates:
                if (isinstance(update, types.UpdateDraftMessage) and
                        isinstance(update.draft, types.DraftMessage) and
                        isinstance(update.peer, types.PeerUser)):
                    logger.debug("user: %s" % self.app.get_users(update.peer.user_id))
                    logger.debug("draft: %s" % update.draft.message)
