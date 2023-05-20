import telegram 
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, JobQueue
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import mysql.connector

TOKEN = '6183521726:AAGqHZywmdqCp6JsoJnbi-AGbS4nRe31xyI'

conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Nerfcs45&",
    database="facility_booking"
    )
    
cursor = conn.cursor()

def main():
    bot = telegram.Bot(token=TOKEN)
    updater = Updater(TOKEN, use_context=True)
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

def update_bookings_table(facility, timing, username):
    #TODO: Key in data into database
    query= "INSERT INTO quick_bookings (facility_id, user_name, timing) VALUES (%s, %s, %s)"
    values= (query.data[facility], username, query.data[timing])
    cursor.execute(query, values)
    conn.commit()
    cursor.close()
    conn.close()
    

def verify_choice(query, context):
    timing_selected = query.data
    response_text = f"{timing_selected} selected \nConfirm booking?"
    keyboard = [[InlineKeyboardButton("Yes", callback_data='Confirm Booking'),
                 InlineKeyboardButton("No", callback_data='Abort Booking')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    context.bot.send_message(chat_id=query.message.chat_id, text=response_text, reply_markup=reply_markup)

def confirm_booking(query, context):
    timing_selected = query.data
    response_text = f"{timing_selected} selected \nConfirm booking?"
    keyboard = [[InlineKeyboardButton("Yes", callback_data='Confirm Booking'),
                 InlineKeyboardButton("No", callback_data='Abort Booking')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if query.data== 'Confirm Booking':
        facility=query.data
        username=query.user_id
        timing=timing_selected
        update_bookings_table(facility, timing, username)
    context.bot.send_message(chat_id=query.message.chat_id, text=response_text, reply_markup=reply_markup)

def set_reminder(query, context):
    #TODO: Add working function.
    context.bot.edit_message_text(chat_id=query.message.chat_id, message_id=query.message.message_id, text="A reminder will be sent to you 15 minutes before the start time.")

main()