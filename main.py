#---------------------------------------IMPORTS--------------------------------------------------------------

from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import ForeignKey, create_engine, Column, Integer, String, DateTime, Boolean, and_
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

#---------------------------------------CONSTANTS--------------------------------------------------------------
MAX_USERNAME_LENGTH = 100
MAX_MESSAGE_LENGTH = 500
MAX_SUBJECT_LENGTH = 500

#---------------------------------------MESSAGES--------------------------------------------------------------

ERROR_SENDER_NOT_REGISTERED = "sender is not registered - message has not been sent, please register first"
ERROR_RECEIVER_NOT_REGISTERED = "reveiver is not registered - message has not been sent"
ERROR_USERNAME_NOT_EXISTS = "username not exists"
ERROR_NO_MESSAGE_TO_SHOW = "there is not messages to show"

MSG_DELETED_SUCCESFULLY = "message deleted succesfully"
MSG_NOT_DELETED = "message NOT deleted - this Id of a message doesn't exists"

STARS_UNDERLINE = "\n ************************************** \n"

MSG_SENDER = "\n sent by: "
MSG_RECEIVER = "\n sent to: "
MSG_DATE = "\n sent at: "
MSG_SUBJECT = "\n subject: "
MSG_BODY = "\n "
MSG_ID = "\n message Id is: "


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///appMessagesDB.db'
engine = create_engine('sqlite:///appMessagesDB.db')
Session = sessionmaker(bind=engine)
session = Session()

# initialize the db
db = SQLAlchemy(app)
Base = declarative_base()


#---------------------------------------CLASSES--------------------------------------------------------------

# create db model
class User(Base):

    __tablename__ = 'Users'

    userId = Column(Integer, primary_key=True, unique = True)
    username = Column(String(MAX_USERNAME_LENGTH), nullable=False, unique = True)
    password = Column(String(100))


# create db model
class Message(Base):

    __tablename__ = 'Messages'

    id = Column(Integer, primary_key=True)
    sender = Column(ForeignKey(User.userId))
    receiver = Column(ForeignKey(User.userId))
    bodyOfTheMessage = Column(String(MAX_MESSAGE_LENGTH))
    subjectOfTheMessage = Column(String(MAX_SUBJECT_LENGTH))
    creationDate = Column(DateTime, default=datetime.utcnow())
    isRead = Column(Boolean, default=False)
    isDeltedBySender = Column(Boolean, default=False)
    isDeltedByReceiver = Column(Boolean, default=False)


    def __str__(self):
        representationOfMessage = MSG_SENDER + convertIdToUsername(self.sender) + MSG_RECEIVER + \
                                  convertIdToUsername(self.receiver) + MSG_DATE + \
                                  self.creationDate.strftime('%m/%d/%Y, %H:%M:%S') + MSG_SUBJECT + \
                                  self.subjectOfTheMessage + MSG_BODY + self.bodyOfTheMessage +  MSG_ID + \
                                  str(self.id)
        return representationOfMessage




Base.metadata.create_all(engine)

#---------------------------------------FUNCTIONS------------------------------------------------------------


def convertUsernameToId(username):
    """
    a function that converts a user name to the relevant ID
    :param username: the given username
    :return: the suitable ID for this user
    """
    userWithThisName = session.query(User).filter(User.username == username).one()
    return userWithThisName.userId

def convertIdToUsername(userId):
    """
    a function that converts a given ID of the user to the username
    :param userId: the given ID
    :return: the relevant username
    """
    userWithThisId = session.query(User).filter(User.userId == userId).one()
    return userWithThisId.username

def checkIfUserExistsByUsername(username):
    """
    a function that check if the username is already taken by another user
    :param username: the given username to check
    :return: True if the user name is taken, else false
    """
    if (session.query(User).filter(User.username == username).count()) == 0:
        return False
    return True

def checkValidMessage(message):
    """
    a function that checks if the sender of the message and the receiver of the message exists/signed up
    :param message: the given message to check its sender and receiver
    :return: relevant ERROR MESSAGE if one of them doesn't exists, else return NONE
    """
    if not checkIfUserExistsByUsername(message.get('sender')):
        return ERROR_SENDER_NOT_REGISTERED

    elif not checkIfUserExistsByUsername(message.get('receiver')):
        return ERROR_RECEIVER_NOT_REGISTERED

    return None

@app.route('/writeMessage', methods=['POST'])
def write_message():
    """
    a functino that takes care of the writing message mechanism
    :return: that the message is sent if the relevant fields are valid, else returns a relevant ERROR MESSAGE
    """
    message = request.get_json()
    errorsInTheMessage = checkValidMessage(message)
    if errorsInTheMessage:
        return {'message': errorsInTheMessage}, 400
    recievedMessage = Message(sender = convertUsernameToId(message.get('sender')),
                              receiver = convertUsernameToId(message.get('receiver')),
                              bodyOfTheMessage = message.get('body'),
                              subjectOfTheMessage = message.get('subject'))
    session.add(recievedMessage)
    session.commit()
    return {'message': "message sent"}, 200


@app.route('/registerUser', methods=['POST'])
def register_new_user():
    """
    a function that take care of the register mechanism of a new user
    :return: a message that the user has registered succesfully if all the relevant fields are valid and if
    the user name is not already taken, else return an informative ERROR MESSAGE
    """
    received = request.get_json()
    if checkIfUserExistsByUsername(received.get('newUsername')):
        #if the user exists then don't allow to register again
        return {'message': "username already used - please try another username"}, 400
    newUser = User(username = received.get('newUsername'), password = 'newPassword')
    session.add(newUser)
    session.commit()
    return {'message': "new user created succesfully"}, 200

def getAllSentMessaggesForUser(userId):
    """
    a function that get all the message sent by a given user (the given input is it's the userId)
    :param userId: the given userId to returns it's sent messages
    :return: only the messages that the user sent and has not deleted
    """
    messagesHolder = session.query(Message).filter(and_(Message.sender == userId, Message.isDeltedBySender
                                                        == False)).all()
    resultString = STARS_UNDERLINE + 'Messages Sent     ' + STARS_UNDERLINE
    resultString = resultString + 'number of messages sent: ' + str(session.query(Message).filter(and_(
        Message.sender == userId, Message.isDeltedBySender  == False)).count()) + '\n'
    for each in messagesHolder:
        resultString = resultString + str(each) + '\n'

    return resultString

def getAllReadMessaggesForUser(userId):
    """
    a function that returns all the messages that's been sent to this user except the deleted ones
    :param userId: the given userId that the messages sent to
    :return: all the messages for this user that he already read
    """
    messagesHolder = session.query(Message).filter(and_(Message.receiver == userId, Message.isRead ==
                                                   True, Message.isDeltedByReceiver == False)).all()
    resultString = STARS_UNDERLINE + 'Messages recieved     ' + STARS_UNDERLINE
    resultString = resultString + 'number of read messages : ' + str(session.query(Message).filter(and_(
        Message.receiver == userId, Message.isRead == True, Message.isDeltedByReceiver == False)).count()) + '\n'
    for each in messagesHolder:
        resultString = resultString + str(each) + '\n'
        # mark the message as been read after showing it
        updateMessageAsReaded(each)
    session.commit()
    return resultString

def getUnreadedMessaggesForUser(userId):
    """
    a function that returns all the unread messages that's been sent to this user
    :param userId: the given userId that the messages sent to
    :return: all the unread messages for this user, after showing them, all of them ,marked as read
    """
    messagesHolder = session.query(Message).filter(Message.receiver == userId, Message.isRead == False).all()
    resultString = STARS_UNDERLINE +'New messages     ' + STARS_UNDERLINE
    resultString = resultString + 'number of new messages recieved: ' + str(session.query(Message).filter(
        Message.receiver == userId, Message.isRead == False).count()) + '\n'
    for each in messagesHolder:
        resultString = resultString + str(each) + '\n'
        # mark the message as been readed after showing it
        updateMessageAsReaded(each)
    session.commit()
    return resultString

# mark the message as been readed after showing it
def updateMessageAsReaded(singleMessage):
    """
    a function that mark a given message as read
    :param singleMessage: the message to mark as read
    :return: void
    """
    singleMessage.isRead = True

@app.route('/getAllMessagesForUser/<userName>', methods=['GET'])
def get_all_messages_for_user(userName):
    """
    a function that returns all the messages that are sent by or sent to a given user, also those he hasn't
    read yet, after showing them will mark them as read, uses different help functions, not showing the
    ones that he deleted (for himself)
    :param userName: the given user name
    :return: all the messages that are relevant to the user but not the ones he deleted for him,
    else returns a relevant ERROR MESSAGE
    """
    #first checking if the user name that has been given exists in the system
    if not checkIfUserExistsByUsername(userName):
        return {'message': ERROR_USERNAME_NOT_EXISTS}, 400
    relevantUserId = convertUsernameToId(userName)

    #gathering all relevant messages as a string
    allMessagesRepresentation = getUnreadedMessaggesForUser(relevantUserId) + '\n' + \
                                getAllReadMessaggesForUser(relevantUserId) + '\n' + \
                                getAllSentMessaggesForUser(relevantUserId)
    return allMessagesRepresentation, 200

@app.route('/getAllUnreadMessagesForUser/<userName>', methods=['GET'])
def get_all_Unread_messages(userName):
    """
    a function that is responsible for the mechanism of this URL using a help function that returns the
    unread messages
    :param userName: the given username
    :return: all the unread messages for a given user and later mark them as read, if the user does not
    exists will return a relevant ERROR MESSAGE
    """
    if not checkIfUserExistsByUsername(userName):
        return {'message': ERROR_USERNAME_NOT_EXISTS}, 400

    relevantUserId = convertUsernameToId(userName)
    unreadedMessagesRepresentation = getUnreadedMessaggesForUser(relevantUserId)

    return unreadedMessagesRepresentation , 200

def getSingleMessageForUser(userId):
    """
    a function that return a single message for a user, it's priority is to show the unread messages first
    (one by one every time it's called) after showing all unreaded messages for a user it will show the
    first message it's recieved, after showing an unread message it will mark it as been read
    :param userId: the given userId
    :return: a string that describes a single message sent to the user as described above, if there is not
    message to show - will return a relevant message
    """
    #if there is a message that is unread it will show one like that and mark it as readed
    if not (session.query(Message).filter(Message.receiver == userId, Message.isRead == False).count())==0:
        unreadedMessage = session.query(Message).filter(and_(Message.receiver == userId, Message.isRead ==
                                                   False, Message.isDeltedByReceiver == False)).first()
        updateMessageAsReaded(unreadedMessage)
        session.commit()
        return str(unreadedMessage)
    # else if there is no unreaded messages, and there is readed messages
    elif not (session.query(Message).filter(Message.receiver == userId, Message.isRead == True).count())==0:
        readedMessage = session.query(Message).filter(and_(Message.receiver == userId, Message.isRead ==
                                                   True, Message.isDeltedByReceiver == False)).first()
        session.commit()
        return str(readedMessage)
    else:
        return ERROR_NO_MESSAGE_TO_SHOW

@app.route('/readMessage/<userName>', methods=['GET'])
def get_message_for_user(userName):
    """
    a function that is responsible for the mechanism of the relevant URL, using a help function that is
    described above
    :param userName: the given username
    :return: a relevant message with priority to unread message, if there is no such it's return the first
    message that the user received, else return that there is not messages to show
    """
    if not checkIfUserExistsByUsername(userName):
        return {'message': ERROR_USERNAME_NOT_EXISTS}, 400
    relevantUserId = convertUsernameToId(userName)
    relevantMessage = getSingleMessageForUser(relevantUserId)

    return str(relevantMessage), 200

def deleteMessageById(messageId, userName):
    """
    a function that deletes a message in different ways, if the sender decides to delete it, it will delete
     it for him, means he can't see it anymore, same mechanism if the receiver decided to delete it, if BOTH
      decides to delete it, it will be deleted from the database
    :param messageId: the ID of the relevant message to delete
    :param userName: the username that wants to delete this message
    :return: a message the message have been deleted sucessfully if the described above worked as planned -
    means that the username is relevant somehow to the message (as a receiver or as a sender) else returns
    that the message doesn't exists -since it's not the buissness of a user that if the message exists if
    he is not relevant
    """
    resultMessage = ''
    #checking if such a message exists
    if session.query(Message).filter(Message.id == messageId).count() == 1:
        relevantMessage = session.query(Message).filter(Message.id == messageId).first()
        #if the sender is also the receiver would like to delete it, message will be deleted from dataBase
        if (relevantMessage.sender == userName and relevantMessage.receiver == userName):
            resultMessage = MSG_DELETED_SUCCESFULLY
            session.query(Message).filter(Message.id == messageId).delete()
            session.commit()
            return resultMessage
        #if the sender would like to delete it, it will be deleted for him (as a sender)
        if (convertUsernameToId(userName) == relevantMessage.sender and relevantMessage.isDeltedBySender ==
            False):
            relevantMessage.isDeltedBySender = True
            resultMessage = MSG_DELETED_SUCCESFULLY
        elif ((convertUsernameToId(userName) == relevantMessage.sender and relevantMessage.isDeltedBySender ==
            True)):
            resultMessage = MSG_NOT_DELETED

        #if the receiver would like to delete it, it will be deleted for him (as a sender)

        if (convertUsernameToId(userName) == relevantMessage.receiver and
                relevantMessage.isDeltedByReceiver == False):
            relevantMessage.isDeltedByReceiver = True
            resultMessage = MSG_DELETED_SUCCESFULLY
        elif ((convertUsernameToId(userName) == relevantMessage.receiver and relevantMessage.isDeltedByReceiver ==
            True)):
            resultMessage = MSG_NOT_DELETED
        if(relevantMessage.isDeltedBySender == True and relevantMessage.isDeltedByReceiver == True):
            session.query(Message).filter(Message.id == messageId).delete()
        session.commit()
        return resultMessage
    else:
        return MSG_NOT_DELETED

@app.route('/deleteMessage/<userName>/<messageId>', methods=['GET'])
def delete_message_by_Id(userName, messageId):
    """
    a function that is responsible for the mechanism of the relevant URL
    :param userName: the given username that likes to dlete a message
    :param messageId: the message the user wants to delete
    :return: a result message of the helper function "deleteMessageById"
    """
    resultMessage = deleteMessageById(messageId, userName)
    return resultMessage, 200


app.run(host="localhost", port=5000)
