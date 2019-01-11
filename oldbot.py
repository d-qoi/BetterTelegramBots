# FeedbackBot
# Created by Alexander Hirschfeld

import argparse
import logging
from pymongo import MongoClient
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, TelegramError
from telegram.ext import Updater, CommandHandler, Filters, MessageHandler
from telegram.ext import CallbackQueryHandler

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# Globals
AUTHTOKEN = None
MCLIENT = None
MDB = None
INFOTEXT = None
WELCOMETEXT = None
asdf = 1

def checkValidCommand(text, username):
    text = text.split()[0]
    try:
        at = text.index('@')+1
        if text[at:] == username:
            return True
        return False
    except ValueError:
        return True


# Utility functions
# Returns the list of chats that a user is admin of.
def getChatsAdmining(uid, username):
    results = MDB.groups.find({'admins': uid})
    listOfChats = list()
    logger.debug("%s is in %i groups as admin" % (username, results.count()))
    for doc in results:
        listOfChats.append({'title': doc['title'], 'id': doc['_id']})
    return listOfChats


# Return a list of chat titles
def getChatList():
    return [[doc['title'], doc['_id']] for doc in MDB.groups.find()]


def updateGroupData(update):
    group = dict()
    chat = update.message.chat
    group['title'] = chat.title
    group['admins'] = [chatmember.user.id for chatmember in chat.get_administrators()]
    result = MDB.groups.update({'_id': chat.id}, group, upsert=True)
    if 'upserted' in result:
        logger.warn("Group %s was accidently deleted from the database." % chat.title)


# User functions
def start(bot, update, user_data):
    if not checkValidCommand(update.message.text, bot.username):
        return
    logger.info("User %s (%s) called start." % (update.message.from_user.username, update.message.from_user.id))
    if update.message.chat.type == "private":
        user_data['active'] = False
        user_data['reply_to'] = False
        admining = getChatsAdmining(update.message.from_user.id, update.message.from_user.username)
        # result = MDB.active.find({'forward_to':{'$in':update.message.chat.id}}).count()
        result = MDB.active.update({'forward_to':update.message.chat.id},{'$pull':{'forward_to':update.message.chat.id}})
        logger.debug("Result of cleanup: %s" % result)
        #logger.debug("Admin of %s" % user_data['admin_of'])
        if admining:
            reply_text = "Hello @%s! You are an Admin! Would you like to give feedback or reply to feedback!" % update.message.from_user.username
            mongoData = {'0':{'chosen':None},
                         '1':{'chosen':None},
                         'reason':'admin_initial'}
            keyboard = [[InlineKeyboardButton('Give Feedback',
                                             callback_data='0')],
                         [InlineKeyboardButton('Reply to Feedback',
                                             callback_data='1')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            MDB.callback_data.update({ '_id' : update.message.from_user.id }, mongoData, upsert=True)
            update.message.reply_text(reply_text, reply_markup=reply_markup)
            user_data['active'] = False
        else:
            reply_text="Hello %s, anything you send to this bot will alert an admin, they should reply quickly.\n" % update.message.from_user.username
            reply_text=reply_text + "We would recommend starting with what you would like to discuss."
            update.message.reply_text(reply_text)
            user_data['active'] = True


def help(bot, update, user_data, chat_data):
    if not checkValidCommand(update.message.text, bot.username):
        return
    logger.debug("User %s (%s) called help." % (update.message.from_user.username, update.message.from_user.id))
    if update.message.chat.type == 'private':
        reply_text = '''

Welcome to this bot!
There are a few useful commands:


    /start: Will restart the bot

    /cancel: Will also restart the bot, will let chat admins choose another thread to respond to.

    /resolve: Will resolve the current thread and remove it from the list.

    /help: Displays this message.

    /info: Will display info text.

If this bot appears to be acting weird or not responding, send /start or /cancel.
This bot was created by @YTKileroy
        '''
        update.message.reply_text(reply_text)
    else:
        update.message.reply_text("Please PM this bot and try /help again. For information, use /info.", quote=False)


def statusReceived(bot, update):
    logger.debug("Message Received")

    if update.message.new_chat_members and update.message.new_chat_members[0].username == bot.username:
        logger.info("Added To Chat %s (%s)" % (update.message.chat.title, update.message.chat.id))
        newGroup = dict()
        chat = update.message.chat
        #newGroup['_id'] = chat.id
        newGroup['title'] = chat.title
        newGroup['admins'] = [chatmember.user.id for chatmember in chat.get_administrators()]
        logger.debug("newGroup: %s" % newGroup)

        MDB.groups.update({'_id':chat.id}, newGroup, upsert=True)
        logger.info("Added %s to the group list" % update.message.chat.title)

    elif update.message.new_chat_members:
        updateGroupData(update)
        logger.info("New member joined the chat.")
        update.message.reply_text(WELCOMETEXT, quote=False)

    elif update.message.left_chat_member and update.message.left_chat_member.username == bot.username:
        MDB.groups.remove({'_id':update.message.chat.id})
        logger.info("Removing entry for %s" % (update.message.chat.title))

# When a user sends a message, it is forwarded to everyone with this method.
def forwardToAll(bot, list_of_chats, from_chat_id, message_id):
    logger.debug("List of chats to forward a message to: %s" % list_of_chats)

    if not list_of_chats: #If there are no chats to foward to.
        return

    for chat in list_of_chats:
        try:
            bot.forward_message(chat_id=chat,
                                from_chat_id=from_chat_id,
                                message_id=message_id)
        except TelegramError as te:
            logger.debug("Unable to send message to %s from %s. May want to remove it, or resolve the thread." %(chat, from_chat_id))
            logger.debug("Error from forward to all: %s" % te)

def sendToAll(bot, message, list_of_chats, user_chat_id):
    timeout = 10 #Timeout in seconds, though this might be a good idea, don't think this bot will be hitting this any time soon
    # This is the bulk of the work in this bot.

    if Filters.forwarded(message):
        message_id = message.message_id
        from_chat = message.forward_from_chat.id
        for chat in list_of_chats:
            try:
                bot.forward_message(chat_id=chat,
                                    from_chat_id=from_chat,
                                    message_id=message_id,
                                    timeout=timeout)
            except TelegramError as te:
                logger.debug("Unable to send message to admin in sendToAll: %s" % te)

        try:
            newMessage = bot.forward_message(chat_id=user_chat_id,
                                             from_chat_id=from_chat,
                                             message_id=message_id,
                                             timeout=timeout)
        # If the user has not responded. Message all of the admins.
        except TelegramError as te:
            logger.debug("Unable to send message to user in sendToAll: %s" % te)
            for chat in list_of_chats:
                try: #error checking in error checking because bot.sendMessage doesn't work for people who haven't messaged the bot.
                    bot.sendMessage(chat_id=chat,
                                    text="Unable to forward message to user, if this persists, resolve this thread, they may have stopped talking to the bot.")
                except TelegramError:
                    pass

    elif Filters.text(message):
        for chat in list_of_chats:
            try:
                bot.send_message(chat_id=chat,
                                 text=message.text,
                                 timeout=timeout)
            except TelegramError as te:
                logger.debug("Unable to send message to admin in sendToAll: %s" % te)
        try:
            newMessage = bot.send_message(chat_id=user_chat_id,
                                          text=message.text,
                                          timeout=timeout)
        except TelegramError as te:
            logger.debug("Unable to send message to user in sendToAll: %s" % te)
            for chat in list_of_chats:
                try:
                    bot.sendMessage(chat_id=chat,
                                    text="Unable to send text message to user, if this persists, resolve this thread, they may have stopped talking to the bot.")
                except TelegramError:
                    pass


    elif Filters.audio(message):
        audio = message.audio.file_id
        for chat in list_of_chats:
            try:
                bot.send_audio(chat_id=chat,
                               audio=audio,
                               timeout=timeout)
            except TelegramError as te:
                logger.debug("Unable to send message to admin in sendToAll: %s" % te)
        try:
            newMessage = bot.send_audio(chat_id=user_chat_id,
                                        audio=audio,
                                        timeout=timeout)
        except TelegramError as te:
            logger.debug("Unable to send message to user in sendToAll: %s" % te)
            for chat in list_of_chats:
                try:
                    bot.sendMessage(chat_id=chat,
                                    text="Unable to send audio message to user, if this persists, resolve this thread, they may have stopped talking to the bot.")
                except TelegramError:
                    pass


    elif Filters.document(message):
        document = message.document.file_id
        for chat in list_of_chats:
            try:
                bot.send_document(chat_id=chat,
                                  document=document,
                                  timeout=timeout)
            except TelegramError as te:
                logger.debug("Unable to send message to admin in sendToAll: %s" % te)
        try:
            newMessage = bot.send_document(chat_id=user_chat_id,
                                           document=document,
                                           timeout=timeout)
        except TelegramError as te:
            logger.debug("Unable to send message to user in sendToAll: %s" % te)
            for chat in list_of_chats:
                try:
                    bot.sendMessage(chat_id=chat,
                                    text="Unable to send document to user, if this persists, resolve this thread, they may have stopped talking to the bot.")
                except TelegramError:
                    pass


    elif Filters.photo(message):
        photo = message.photo[0].file_id
        caption = ""
        if message.caption:
            caption = message.caption
        for chat in list_of_chats:
            try:
                bot.send_photo(chat_id=chat,
                               photo=photo,
                               caption=caption,
                               timeout=timeout)
            except TelegramError as te:
                logger.debug("Unable to send message to admin in sendToAll: %s" % te)
        try:
            newMessage = bot.send_photo(chat_id=user_chat_id,
                                        photo=photo,
                                        caption=caption,
                                        timeout=timeout)
        except TelegramError as te:
            logger.debug("Unable to send message to user in sendToAll: %s" % te)
            for chat in list_of_chats:
                try:
                    bot.sendMessage(chat_id=chat,
                                    text="Unable to send photo to user, if this persists, resolve this thread, they may have stopped talking to the bot.")
                except TelegramError:
                    pass

    elif Filters.sticker(message):
        sticker = message.sticker.file_id
        for chat in list_of_chats:
            try:
                bot.send_sticker(chat_id=chat,
                                 sticker=sticker,
                                 timeout=timeout)
            except TelegramError as te:
                logger.debug("Unable to send messages to admin in SendToAll: %s" % te)
        try:
            newMessage = bot.send_sticker(chat_id=user_chat_id,
                                          sticker=sticker,
                                          timeout=timeout)
        except TelegramError as te:
            logger.debug("Unable to send message to user in sendToAll: %s" % te)
            for chat in list_of_chats:
                try:
                    bot.sendMessage(chat_id=chat,
                                    text="Unable to send sticker to user, if this persists, resolve this thread, they may have stopped talking to the bot.")
                except TelegramError:
                    pass

    elif Filters.voice(message):
        voice = message.voice.file_id
        for chat in list_of_chats:
            try:
                bot.send_voice(chat_id=chat,
                               voice=voice,
                               timeout=timeout)
            except TelegramError as te:
                logger.debug("Unable to send message to admin in sendToAll: %s " % te)
        try:
            newMessage = bot.send_voice(chat_id=user_chat_id,
                                        voice=voice,
                                        timeout=timeout)
        except TelegramError as te:
            logger.debug("Unable to send message to user in sendToAll: %s" % te)
            for chat in list_of_chats:
                try:
                    bot.sendMessage(chat_id=chat,
                                    text="Unable to send voice message to user, if this persists, resolve this thread, they may have stopped talking to the bot.")
                except TelegramError:
                    pass

    elif Filters.video(message):
        video = message.video.file_id
        for chat in list_of_chats:
            try:
                bot.send_video(chat_id=chat,
                               video=video,
                               timeout=timeout)
            except TelegramError as te:
                logger.debug("Unable to send message to admin in sendToAll: %s" % te)
        try:
            newMessage = bot.send_video(chat_id=user_chat_id,
                                        video=video,
                                        timeout=timeout)
        except TelegramError as te:
            logger.debug("Unable to send message to user in sendToAll: %s" % te)
            for chat in list_of_chats:
                try:
                    bot.sendMessage(chat_id=chat,
                                    text="Unable to send message to user, if this persists, resolve this thread, they may have stopped talking to the bot.")
                except TelegramError:
                    pass

    elif Filters.contact(message):
        phone_number = message.contact.phone_number
        first_name = message.contact.first_name
        last_name = message.contact.last_name
        for chat in list_of_chats:
            try:
                bot.send_contact(chat_id=chat,
                                 phone_number=phone_number,
                                 first_name=first_name,
                                 last_name=last_name,
                                 timeout=timeout)
            except TelegramError as te:
                logger.debug("Unbable to send message to admin in sendToAll: %s" % te)
        try:
            newMessage = bot.send_contact(chat_id=user_chat_id,
                                          phone_number=phone_number,
                                          first_name=first_name,
                                          last_name=last_name,
                                          timeout=timeout)
        except TelegramError as te:
            logger.debug("Unable to send message to user in sendToAll: %s" % te)
            for chat in list_of_chats:
                try:
                    bot.sendMessage(chat_id=chat,
                                    text="Unable to send contact to user, if this persists, resolve this thread, they may have stopped talking to the bot.")
                except TelegramError:
                    pass

    elif Filters.location(message):
        lat = message.location.latitude
        lon = message.location.longitude
        for chat in list_of_chats:
            try:
                bot.send_location(chat_id=chat,
                                 longitude=lon,
                                 latitude=lat,
                                 timeout=timeout)
            except TelegramError as te:
                logger.debug("Unable to send message to admin in sendToAll: %s" % te)
        try:
            newMessage = bot.send_location(chat_id=user_chat_id,
                                          longitude=lon,
                                          latitude=lat,
                                          timeout=timeout)
        except TelegramError as te:
            logger.debug("Unable to send message to user in sendToAll: %s" % te)
            for chat in list_of_chats:
                try:
                    bot.sendMessage(chat_id=chat,
                                    text="Unable to send location to user, if this persists, resolve this thread, they may have stopped talking to the bot.")
                except TelegramError:
                    pass

    else:
        logger.warning("Message %s not handled in SendToAll")
        raise TelegramError("No handler for forwarding.")

    MDB.active.update({'_id':user_chat_id},
                      {'$push':{'log':newMessage.message_id}})

def alertAdmins(bot, username):
    admins = []
    logger.debug('alerting admins:')
    for group in MDB.groups.find():
        logger.debug("Admins in group %s: %s" %(group['title'], group['admins']))
        admins += group['admins']
    admins = set(admins)
    for admin in admins:
        try:
            bot.send_message(chat_id=admin,
                            text="%s is sending feedback, send /cancel to select and respond to them." % username)
        except TelegramError as te:
            logger.debug("Not all admins are interacting with the bot.")
            logger.debug("Error in alert Admins: %s" % te)


def messageReceived(bot, update, user_data):
    if update.message.chat.type == 'private':
        # In case there was a reset of this server, reset everything, then check to see if they were chatting.
        if not 'active' in user_data and not 'reply_to' in user_data:
            user_data['active']=True
            user_data['reply_to'] = None
            if getChatsAdmining(update.message.from_user.id, update.message.from_user.username):
                reply_text = "There was a server reset for this bot. You were previously replying to:\n"
                results = MDB.active.find({'forward_to' : update.message.chat.id})
                #repairing things
                if results.count() > 1: #If their ID was in two chats
                    MDB.active.update_many(
                        {'forward_to' : update.message.chat.id},
                        {'$pull':{'forward_to':update.message.chat.id}})
                    reply_text += "None\n Type /cancel to restart or if you would like to give feedback, start typing."
                elif results.count() == 0: # If they weren't replying.
                    reply_text += "None\n Type /cancel to restart or if you would like to give feedback, start typing."
                elif results.count == 1: # If they were interacting with one user.
                    results = results.next()
                    reply_to = results['_id']
                    reply_to_name = results['name']
                    reply_text += reply_to_name
                    reply_text += '\nThere may be message you haven\'t received, hit /cancel and re-select this user again to receive them'
                    user_data['active']=False
                    user_data['reply_to'] = reply_to
                else:
                    logger.warn("User %s (%s) managed to break the database if statement in messageReceived" % (update.message.from_user.username, update.message.from_user.id))
                update.message.reply_text(reply_text)
            else: # They were a regular user, re-start this command now that user_data['active'] is reset.
                messageReceived(bot, update, user_data)

        if user_data['active']: # If they are currently giving feed back.
            user_data['reply_to'] = None
            message = update.message
            user = message.from_user
            chat_id = message.chat.id
            user_id = update.message.from_user.id
            logger.debug("User_id %s" % user_id)
            created = MDB.active.update(
                {'_id':chat_id},
                {'$set': {
                    'username':user.username,
                    'name':user.first_name + " " + user.last_name,
                    'id' : user_id
                    },
                 '$push': {
                    'log': message.message_id,
                    }
                }, upsert=True)
            logger.debug("Message Received created? %s" % 'upserted' in created)
            if 'upserted' in created:
                logger.debug("Created, alerting admins.")
                alertAdmins(bot, user.first_name + " " + user.last_name)

            list_of_chats = MDB.active.find({'_id':chat_id})

            if list_of_chats.count() > 0:
                list_of_chats = list_of_chats.next()
                logger.debug("List_of_chats find results %s" % list_of_chats)
                if not 'forward_to' in list_of_chats:
                    MDB.active.update({'_id':chat_id},{'$set':{'forward_to':[]}})
                else:
                    list_of_chats = list_of_chats['forward_to']
                    forwardToAll(bot, list_of_chats, chat_id, message.message_id)

        elif user_data['reply_to']:
            user_data['active'] = False
            message = update.message
            #user = message.from_user
            try:
                list_of_chats = MDB.active.find({'_id':user_data['reply_to']})
                if list_of_chats.count() == 0:
                    update.message.reply_text("This session may have been resolved, use /cancel to select another user.")
                    return
                list_of_chats = list_of_chats.next()['forward_to']
                sendToAll(bot, message, list_of_chats, user_data['reply_to'])
            except TelegramError:
                update.message.reply_text("This session may have been resolved, use /cancel to select another user.")


def callbackResponseHandler(bot, update, user_data):
    #logger.debug("callbackResponseHandler %s" % (update.callback_query))

    query = update.callback_query
    qdata = query.data
    message_id = query.message.message_id
    chat_id = query.message.chat_id
    user_id = query.from_user.id
    result = MDB.callback_data.find({'_id':user_id}).next()
    #blankKeyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Enjoy", callback_data='-1')]])

    # Long list of choices for the inlinebutton responses
    if result['reason'] == 'admin_initial':
        # This means they chose to give feedback
        if qdata == '0':
            reply_text = 'Anything you send to this bot will be considered feedback. We recommend starting with what you would like to provide feedback for.\n'
            reply_text = reply_text + "Hitting /cancel will take you back to the initial options."
            user_data['active'] = True
            user_data['reply_to'] = None
            bot.editMessageText(text=reply_text,
                                chat_id=chat_id,
                                message_id=message_id)
            MDB.callback_data.remove({'_id':user_id})
        # Means they chose to answer feedback
        elif qdata == '1':
            reply_text = "Which User would you like to give feedback too?"
            userlist = [[doc['name'],doc['_id']] for doc in MDB.active.find()]
            mongoData = dict()
            keyboard = list()
            for i in range(0,len(userlist)):
                keyboard.append( [InlineKeyboardButton(userlist[i][0], callback_data=str(i))] )
                mongoData[str(i)] = {'chosen':userlist[i][1],'name':userlist[i][0]}
            mongoData['reason'] = 'setting_user'
            reply_markup = InlineKeyboardMarkup(keyboard)
            bot.editMessageText(text=reply_text,
                                chat_id=chat_id,
                                message_id=message_id,
                                reply_markup=reply_markup)
            MDB.callback_data.update({ '_id' : user_id }, mongoData)
    elif result['reason'] == 'setting_user':
        choice = result[qdata]
        reply_text = "You are now replying to %s.\n" % choice['name']
        reply_text += "Type /cancel to stop and restart."
        user_data['reply_to'] = choice['chosen']
        MDB.active.update({'_id':choice['chosen']},{'$addToSet':{'forward_to':chat_id}})
        result = MDB.active.find({'_id':choice['chosen']})
        if result.count() > 0:
            result = result.next()
            chatlog = result['log']
        else:
            chatlog = []
        keyboard = [[InlineKeyboardButton('Forward All past messages',callback_data='0')]]
        chatlength = len(chatlog)
        if chatlength > 50:
            keyboard = [[InlineKeyboardButton('Forward last 50 messages',callback_data = '1')]]
        if chatlength > 25:
            keyboard.append([InlineKeyboardButton('Forward last 25 messages', callback_data = '2')])
        if chatlength > 10:
            keyboard.append([InlineKeyboardButton('Forward last 10 messages', callback_data = '3')])
        mongoData = dict()
        mongoData['reason'] = 'forward_messages'
        mongoData['0'] = -1
        mongoData['1'] = 50
        mongoData['2'] = 25
        mongoData['3'] = 10
        logger.debug("Editing text for a message.")
        bot.editMessageText(text=reply_text,
                            chat_id=chat_id,
                            message_id=message_id,
                            reply_markup=InlineKeyboardMarkup(keyboard))
        MDB.callback_data.update({ '_id' : user_id }, mongoData)

    elif result['reason'] == 'forward_messages':
        logger.debug("Editing text for a message.")
        bot.editMessageText(text='Enjoy',
                            chat_id=chat_id,
                            message_id=message_id)

        logger.debug("Forwarding messages from %s's history." % query.from_user.username)
        log = MDB.active.find({'_id':user_data['reply_to']}).next()
        logger.debug("active data %s" % log)
        log = log['log']
        logger.debug("Messages %s" % log)

        if qdata == '0':
            count = 0
        else:
            count = result[qdata]

        for message in log[-count:]:
            try:
                bot.forward_message(chat_id = chat_id,
                                    from_chat_id = user_data['reply_to'],
                                    message_id = message)
            except TelegramError:
                bot.send_message(chat_id=chat_id,
                                 text="This message was deleted, if this occurs every time, the user might have deleted this bot. Resolving this chat may be a good idea.")



def resolve(bot, update, user_data):
    if not checkValidCommand(update.message.text, bot.username):
        return
    if update.message.chat.type == 'private':
        logger.info("User %s (%s) resolved a chat." % (update.message.from_user.username, update.message.from_user.id))
        try:
            if user_data['reply_to']:
                logger.info("They are an admin.")
                msg = update.message.reply_text("This session has been resolved. Send this bot a message to start a new thread.")
                list_of_chats = MDB.active.find({'_id':user_data['reply_to']}).next()['forward_to']
                sendToAll(bot, msg, list_of_chats, user_data['reply_to'])
                MDB.active.remove({"_id":user_data['reply_to']})

            elif user_data['active']:
                logger.info("They are a user.")
                msg = update.message.reply_text("This session has been resolved by the user. Send this bot a message to start a new thread.")
                list_of_chats = MDB.active.find({'_id':update.message.chat.id}).next()['forward_to']
                forwardToAll(bot, list_of_chats, update.message.chat.id, msg.message_id)
                MDB.active.remove({"_id": update.message.chat.id})
        except KeyError:
            update.message.reply_text("Please send /start.")


# A utility function, this is what is called when the job created in main runs
def updateChatList(bot, job):
    logger.debug("-----------------------updatedChatList--------------------")
    logger.info("Updating the chat list")
    results = MDB.groups.find()
    for doc in results:
        try:
            chat = bot.getChat(chat_id=doc['_id'])
            logger.info("Chat %s (%s) responded." % (chat.title, chat.id))
            admins = [chatmember.user.id for chatmember in bot.getChatAdministrators(chat_id=doc['_id'])]
            MDB.groups.find_one_and_update({'_id':doc['_id']},
                                           { '$set' : {'title':chat.title, "admins":admins}})
        except TelegramError as te:
            logger.warning("Removing %s (%s) from the database, it is not responding, re-add the bot if this is incorrect." % (doc['title'],doc['_id']))
            logger.debug("Error received: %s" % (str(te)))
            #MDB.groups.remove({'_id':doc['_id']})

        except:
            logger.info("Other error when checking %s (%s), check networking" % (doc['title'],doc['_id']))

def info(bot, update):
    if not checkValidCommand(update.message.text, bot.username):
        return
    if update.message.chat.type != 'private':
        updateGroupData(update)
    update.message.reply_text(INFOTEXT, quote=False)


def error(bot, update, error):
    logger.warn('Update "%s" cause error "%s"' %(update, error))


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

def main():
    try:
        serverInfo = MCLIENT.server_info()
        logger.info("Connected to Mongo Server: %s." % serverInfo)
    except:
        logger.error("Could not connect to the Mongo Server.")
        raise
    updater = Updater(AUTHTOKEN)

    dp = updater.dispatcher

    dp.add_handler(CommandHandler('start', start, pass_user_data=True))
    dp.add_handler(CommandHandler('cancel', start, pass_user_data=True))
    dp.add_handler(CommandHandler('resolve', resolve, pass_user_data=True))
    dp.add_handler(CommandHandler('help', help, pass_user_data=True, pass_chat_data=True))
    dp.add_handler(CommandHandler('info', info))

    dp.add_handler(CallbackQueryHandler(callbackResponseHandler, pass_user_data=True))

    dp.add_handler(MessageHandler(Filters.status_update, statusReceived))
    dp.add_handler(MessageHandler(Filters.all, messageReceived, pass_user_data=True))

    dp.add_error_handler(error)

    updater.start_polling()

    updater.job_queue.run_repeating(updateChatList, 3600, first=60, name="Update Admins Job")

    updater.idle()


if __name__ == '__main__':
    startFromCLI()
    main()
