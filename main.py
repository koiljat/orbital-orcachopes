import telegram
from telegram.ext import CommandHandler, Updater

TOKEN = '6183521726:AAGqHZywmdqCp6JsoJnbi-AGbS4nRe31xyI'

bot = telegram.Bot(token=TOKEN)
updater = Updater(token=TOKEN, use_context=True)
dispatcher = updater.dispatcher

def start(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text="This is a test")

start_handler = CommandHandler('start', start)
dispatcher.add_handler(start_handler)

def book(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text="Select booking")

book_handler = CommandHandler('book', book)
dispatcher.add_handler(book_handler)

updater.start_polling()

import mysql.connector

connection = mysql.connector.connect(
    host="localhost",
    port=3306,  
    user="root",
    password="Nerfcs45&",
    database="Orbital Datab"
)
