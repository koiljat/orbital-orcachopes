import telegram
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import mysql.connector

conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Password1!",
    database="facility_booking"
)
cursor = conn.cursor()

TOKEN = '6183521726:AAGqHZywmdqCp6JsoJnbi-AGbS4nRe31xyI'

def main():
    bot = telegram.Bot(token=TOKEN)
    updater = Updater(token=TOKEN, use_context=True)

    dispatcher = updater.dispatcher
    start_handler = CommandHandler('start', start)
    button_handler = CallbackQueryHandler(button)

    dispatcher.add_handler(start_handler)
    dispatcher.add_handler(button_handler)
    updater.start_polling()

def start(update, context):
    chat_id = update.effective_chat.id
    username = update.effective_chat.username
    first_name = update.effective_chat.first_name

    keyboard = [[InlineKeyboardButton("Quick Booking", callback_data='Quick Booking')],
                [InlineKeyboardButton("Check Booking", callback_data='Check Booking')],
                [InlineKeyboardButton("Advanced Booking", callback_data='Advanced Booking')],
                [InlineKeyboardButton("Report Issue", callback_data='Report Issue')]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    context.bot.send_message(chat_id=chat_id, text="What would you like to do today?", reply_markup=reply_markup)

def button(update, context):
    query = update.callback_query
    response = query.data

    actions = {
        "Quick Booking": show_facility_options,
        "Check Booking": check_bookings,
        "Advanced Booking": advanced_booking,
        "Report Issue": report_issue,
        "Pool Table": show_timing_options,
        "Mahjong Table": show_timing_options,
        "Foosball": show_timing_options,
        "Darts": show_timing_options,
        "Session 1": confirm_booking,
        "Accept Reminder": set_reminder,
        "Reject Reminder": reject_reminder
    }

    if response in actions:
        actions[response](query, context)
    else:
        context.bot.send_message(chat_id=query.message.chat_id, text="Unknown response!")

def advanced_booking(query, context):
    pass

def report_issue(query, context):
    pass

def check_bookings(query, context):
    pass

def reject_reminder(query, context):
    text = "Thank you for booking! \nPlease remember to cancel your booking if you are not able to make it for the session."
    context.bot.edit_message_text(chat_id=query.message.chat_id, message_id=query.message.message_id, text=text)

def show_facility_options(query, context):
    keyboard = [[InlineKeyboardButton("Pool Table", callback_data='Pool Table')],
                [InlineKeyboardButton("Mahjong Table", callback_data='Mahjong Table')],
                [InlineKeyboardButton("Foosball", callback_data='Foosball')],
                [InlineKeyboardButton("Darts", callback_data='Darts')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    context.bot.edit_message_text(chat_id=query.message.chat_id, message_id=query.message.message_id, text="Select your facility", reply_markup=reply_markup)

def show_timing_options(query, context):
    keyboard = [[InlineKeyboardButton("7:00 to 7:30", callback_data='Session 1'),
                 InlineKeyboardButton("7:30 to 8:00", callback_data='Session 2')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    context.bot.edit_message_text(chat_id=query.message.chat_id, message_id=query.message.message_id, text="Select your timing", reply_markup=reply_markup)

def confirm_booking(query, context):
    confirm_text = "Booking confirmed!\nBookingId: 0001\nFacility: Pool Table\nTime: 7:00 to 7:30\n"

    facility = query.data
    timing = "Session 1"
    user_id = query.from_user.id
    username = query.from_user.username

    input = "INSERT INTO bookings (facilitiy_id, user_name, booking_date, start_time, end_time) VALUES (%s, %s, %s, %s, %s)"
    values = (1, 1, 1, 1, 1)
    cursor.execute(input, values)
    conn.commit()

    context.bot.edit_message_text(chat_id=query.message.chat_id, message_id=query.message.message_id, text=confirm_text)
    keyboard = [[InlineKeyboardButton("Yes", callback_data='Accept Reminder'),
                 InlineKeyboardButton("No", callback_data='Reject Reminder')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    context.bot.send_message(chat_id=query.message.chat_id, text="Would you like to set a reminder?", reply_markup=reply_markup)

def set_reminder(query, context):
    context.bot.edit_message_text(chat_id=query.message.chat_id, message_id=query.message.message_id, text="A reminder will be sent to you 15 minutes before the start time.")

main()