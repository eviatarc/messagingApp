# ---------------------------------------IMPORTS--------------------------------------------------------------
import json

from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import ForeignKey, create_engine, Column, Integer, String, DateTime, Boolean, and_, desc
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required, JWTManager

# ---------------------------------------CONSTANTS--------------------------------------------------------------
MAX_USERNAME_LENGTH = 100
MAX_MESSAGE_LENGTH = 500
MAX_SUBJECT_LENGTH = 500

# ---------------------------------------MESSAGES--------------------------------------------------------------

ERROR_SENDER_NOT_REGISTERED = "sender is not registered - message has not been sent, please register first"
ERROR_RECEIVER_NOT_REGISTERED = "reveiver is not registered - message has not been sent"
ERROR_USERNAME_NOT_EXISTS = "username not exists"
ERROR_NO_MESSAGE_TO_SHOW = "there is not messages to show"

MSG_DELETED_SUCCESFULLY = "message deleted successfully"
MSG_NOT_DELETED = "message NOT deleted - this Id of a message doesn't exists"

MSG_SENDER = "\n sent by: "
MSG_RECEIVER = "\n sent to: "
MSG_DATE = "\n sent at: "
MSG_SUBJECT = "\n subject: "
MSG_BODY = "\n "
MSG_ID = "\n message Id is: "

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///appMessagesDB.db'
engine = create_engine('sqlite:///appMessagesDB.db?check_same_thread=False')
Session = sessionmaker(bind=engine)
session = Session()

# initialize the db
db = SQLAlchemy(app)
Base = declarative_base()

# Setup the Flask-JWT-Extended extension
app.config["JWT_SECRET_KEY"] = "super-secret-key-for-jwt-extended-it's-so-secret-nobody-would-guess-it"
jwt = JWTManager(app)


# ---------------------------------------CLASSES--------------------------------------------------------------

# create db model
class User(Base):
    __tablename__ = 'Users'

    userId = Column(Integer, primary_key=True, unique=True)
    username = Column(String(MAX_USERNAME_LENGTH), nullable=False, unique=True)
    password = Column(String(100))


# create db model
class Message(Base):
    __tablename__ = 'Messages'

    id = Column(Integer, primary_key=True)
    sender = Column(ForeignKey(User.userId))
    receiver = Column(ForeignKey(User.userId))
    bodyOfTheMessage = Column(String(MAX_MESSAGE_LENGTH))
    subjectOfTheMessage = Column(String(MAX_SUBJECT_LENGTH))
    creationDate = Column(DateTime, default=datetime.now())
    isRead = Column(Boolean, default=False)
    isDeltedBySender = Column(Boolean, default=False)
    isDeltedByReceiver = Column(Boolean, default=False)

    def __str__(self):
        representationOfMessage = MSG_SENDER + convertIdToUsername(self.sender) + MSG_RECEIVER + \
                                  convertIdToUsername(self.receiver) + MSG_DATE + \
                                  self.creationDate.strftime('%m/%d/%Y, %H:%M:%S') + MSG_SUBJECT + \
                                  self.subjectOfTheMessage + MSG_BODY + self.bodyOfTheMessage + MSG_ID + \
                                  str(self.id)
        return representationOfMessage

    def to_json(self):
        return {
            'id': self.id,
            'sender': convertIdToUsername(self.sender),
            'receiver': convertIdToUsername(self.receiver),
            'subject': self.subjectOfTheMessage,
            'body': self.bodyOfTheMessage,
            'created_at': self.creationDate,
        }


Base.metadata.create_all(engine)


# ---------------------------------------FUNCTIONS------------------------------------------------------------

@app.route("/login", methods=["POST"])
def login():
    username = request.json.get("username", None)
    password = request.json.get("password", None)

    target_user = session.query(User).filter(and_(User.username == username, User.password ==
                                                  password)).first()
    print(target_user)
    if target_user is None:
        return jsonify({"msg": "Bad username or password"}), 401

    access_token = create_access_token(identity=target_user.userId)
    # the returned token is used for any other actions as the user is logged in, it's valid only for 15
    # minutes
    return jsonify(access_token=access_token)


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


def checkValidMessage(message, relevantUserId):
    """
    a function that checks if the sender of the message and the receiver of the message exists/signed up
    :param message: the given message to check its sender and receiver
    :return: relevant ERROR MESSAGE if one of them doesn't exists, else return NONE
    """
    if not checkIfUserExistsByUsername(convertIdToUsername(relevantUserId)):
        return ERROR_SENDER_NOT_REGISTERED

    elif not checkIfUserExistsByUsername(message.get('receiver')):
        return ERROR_RECEIVER_NOT_REGISTERED

    return None


@app.route('/writeMessage', methods=['POST'])
@jwt_required()
def write_message():
    """
    a function that takes care of the writing message mechanism
    :return: that the message is sent if the relevant fields are valid, else returns a relevant ERROR MESSAGE
    """
    message = request.get_json()
    relevantIdOfSender = get_jwt_identity()
    errorsInTheMessage = checkValidMessage(message, relevantIdOfSender)
    if errorsInTheMessage:
        return {'message': errorsInTheMessage}, 400
    recievedMessage = Message(sender=relevantIdOfSender,
                              receiver=convertUsernameToId(message.get('receiver')),
                              bodyOfTheMessage=message.get('body'),
                              subjectOfTheMessage=message.get('subject'))
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
        # if the user exists then don't allow to register again
        return {'message': "username already used - please try another username"}, 400
    newUser = User(username=received.get('newUsername'), password=received.get('newPassword'))
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
                                                        is False)).all()

    return {'sent messages': [message.to_json() for message in messagesHolder]}


def getAllReadMessaggesForUser(userId):
    """
    a function that returns all the messages that's been sent to this user except the deleted ones
    :param userId: the given userId that the messages sent to
    :return: all the messages for this user that he already read
    """
    messagesHolder = session.query(Message).filter(and_(Message.receiver == userId, Message.isRead ==
                                                        True, Message.isDeltedByReceiver == False)).all()

    return {'read messages': [message.to_json() for message in messagesHolder]}


def getUnreadedMessagesForUser(userId):
    """
    a function that returns all the unread messages that's been sent to this user
    :param userId: the given userId that the messages sent to
    :return: all the unread messages for this user, after showing them, all of them ,marked as read
    """
    messagesHolder = session.query(Message).filter(Message.receiver == userId, Message.isRead == False).all()

    for each in messagesHolder:
        # mark the message as been read after showing it
        updateMessageAsReaded(each)

    return {'unread messages': [message.to_json() for message in messagesHolder]}


def updateMessageAsReaded(singleMessage):
    """
    a function that mark a given message as read
    :param singleMessage: the message to mark as read
    :return: void
    """
    singleMessage.isRead = True
    session.commit()


@app.route('/getAllMessages', methods=['GET'])
@jwt_required()
def get_all_messages_for_user():
    """
    a function that returns all the messages that are sent by or sent to a given user, also those he hasn't
    read yet, after showing them will mark them as read, uses different help functions, not showing the
    ones that he deleted (for himself)
    :return: all the messages that are relevant to the user but not the ones he deleted for him,
    else returns a relevant ERROR MESSAGE
    """

    relevantUserId = get_jwt_identity()

    # gathering all relevant messages
    readMessages = getAllReadMessaggesForUser(relevantUserId)
    unreadMessages = getUnreadedMessagesForUser(relevantUserId)
    sentMessages = getAllSentMessaggesForUser(relevantUserId)

    resuletDictionary = {}
    resuletDictionary.update(unreadMessages)
    resuletDictionary.update(readMessages)
    resuletDictionary.update(sentMessages)

    return resuletDictionary, 200


@app.route('/getAllUnreadMessages', methods=['GET'])
@jwt_required()
def get_all_Unread_messages():
    """
    a function that is responsible for the mechanism of this URL using a help function that returns the
    unread messages
    :return: all the unread messages for a given user (a logged in user) and later mark them as read,
    if the user does not exists will return a relevant ERROR MESSAGE
    """

    relevantUserId = get_jwt_identity()

    return getUnreadedMessagesForUser(relevantUserId), 200


# todo: to change the return values

def getSingleMessageForUser(userId):
    """
    a function that return a single message for a user, it's priority is to show the unread messages first
    (one by one every time it's called) after showing all unread messages for a user it will show the
    first message it's recieved, after showing an unread message it will mark it as been read
    :param userId: the given userId
    :return: a string that describes a single message sent to the user as described above, if there is not
    message to show - will return a relevant message
    """
    # if there is a message that is unread it will show one like that and mark it as read - will show the
    # oldest one
    if not (session.query(Message).filter(Message.receiver == userId, Message.isRead == False).count()) == 0:
        unreadMessage = session.query(Message).filter(and_(Message.receiver == userId, Message.isRead ==
                                                           False,
                                                            Message.isDeltedByReceiver == False)).first()
        updateMessageAsReaded(unreadMessage)
        session.commit()
        return unreadMessage
    # else if there is no unread messages, and there is read messages it will show the most recent one
    elif not (session.query(Message).filter(Message.receiver == userId, Message.isRead == True).count()) == 0:
        readedMessage = session.query(Message).filter(and_(Message.receiver == userId, Message.isRead ==
                                                           True, Message.isDeltedByReceiver ==
                                                           False)).order_by(desc(Message.id)).first()
        if readedMessage is None:
            return ERROR_NO_MESSAGE_TO_SHOW
        return readedMessage
    else:
        return ERROR_NO_MESSAGE_TO_SHOW


@app.route('/readMessage', methods=['GET'])
@jwt_required()
def get_message_for_user():
    """
    a function that is responsible for the mechanism of the relevant URL, using a help function that is
    described above
    :return: a relevant message with priority to unread message, if there is no such it's return the first
    message that the user received, else return that there is not messages to show
    """

    relevantUserId = get_jwt_identity()
    relevantMessage = getSingleMessageForUser(relevantUserId)
    if relevantMessage == ERROR_NO_MESSAGE_TO_SHOW:
        return {"message": relevantMessage}, 200
    # todo: to change the return value if the internal function return an error!!!!
    return relevantMessage.to_json(), 200


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
    # checking if such a message exists
    if session.query(Message).filter(Message.id == messageId).count() == 1:
        relevantMessage = session.query(Message).filter(Message.id == messageId).first()
        # if the sender is also the receiver would like to delete it, message will be deleted from dataBase
        if (relevantMessage.sender == userName and relevantMessage.receiver == userName):
            resultMessage = MSG_DELETED_SUCCESFULLY
            session.query(Message).filter(Message.id == messageId).delete()
            session.commit()
            return resultMessage
        # if the sender would like to delete it, it will be deleted for him (as a sender)
        if (convertUsernameToId(userName) == relevantMessage.sender and relevantMessage.isDeltedBySender ==
                False):
            relevantMessage.isDeltedBySender = True
            resultMessage = MSG_DELETED_SUCCESFULLY
        elif ((convertUsernameToId(userName) == relevantMessage.sender and relevantMessage.isDeltedBySender ==
               True)):
            resultMessage = MSG_NOT_DELETED

        # if the receiver would like to delete it, it will be deleted for him (as a sender)

        if (convertUsernameToId(userName) == relevantMessage.receiver and
                relevantMessage.isDeltedByReceiver == False):
            relevantMessage.isDeltedByReceiver = True
            resultMessage = MSG_DELETED_SUCCESFULLY
        elif (
                (convertUsernameToId(
                    userName) == relevantMessage.receiver and relevantMessage.isDeltedByReceiver ==
                 True)):
            resultMessage = MSG_NOT_DELETED
        if (relevantMessage.isDeltedBySender == True and relevantMessage.isDeltedByReceiver == True):
            session.query(Message).filter(Message.id == messageId).delete()
        session.commit()
        return resultMessage
    else:
        return MSG_NOT_DELETED


@app.route('/deleteMessage/<messageId>', methods=['DELETE'])
@jwt_required()
def delete_message_by_Id(messageId):
    """
    a function that is responsible for the mechanism of the relevant URL
    :param messageId: the message the user wants to delete
    :return: a result message of the helper function "deleteMessageById"
    """
    relevantUserId = get_jwt_identity()
    resultMessage = deleteMessageById(messageId, convertIdToUsername(relevantUserId))
    return {"message": resultMessage}, 200


if __name__ == '__main__':
    app.run(debug=True, use_reloader=True, port=5000)
