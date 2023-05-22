import telegram
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import mysql.connector
from mysql.connector import Error
import logging
import pytz
from datetime import date, datetime, time

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                     level=logging.INFO)

TOKEN = '6183521726:AAGqHZywmdqCp6JsoJnbi-AGbS4nRe31xyI'

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
    keyboard = [[InlineKeyboardButton("Quick Booking", callback_data='Quick Booking')],
                [InlineKeyboardButton("Check Booking", callback_data='Check Booking')],
                [InlineKeyboardButton("Advanced Booking", callback_data='Advanced Booking')],
                [InlineKeyboardButton("Report Issue", callback_data='Report Issue')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    context.bot.send_message(chat_id=update.effective_chat.id, text="What would you like to do today?", reply_markup=reply_markup)

def button(update, context):
    query = update.callback_query
    response = query.data

    actions = {
        "Quick Booking": show_facility_options,
        "Check Booking": check_bookings,
        "Advanced Booking": advanced_booking,
        "Report Issue": report_issue,
        #TODO: Use list to store the facilities.
        "Pool Table": show_timing_options,
        "Mahjong Table": show_timing_options,
        "Foosball": show_timing_options,
        "Darts": show_timing_options,
        "Confirm Booking": confirm_booking,
        "Accept Reminder": set_reminder,
        "Reject Reminder": reject_reminder,
        "Accept Booking": accept_booking,
        "Abort Booking": abort_booking
    }

    if response in actions:
        actions[response](query, context)
    elif response.find("Session") != -1:
        actions["Confirm Booking"](query, context)
    else:
        context.bot.send_message(chat_id=query.message.chat_id, text="Unknown response!")

def advanced_booking(query, context):
    pass

def report_issue(query, context):
    pass

def check_bookings(query, context):
    pass

def abort_booking(query, context):
    text = "Booking terminated. \nThank you for using ORCAChopes."
    context.bot.edit_message_text(chat_id=query.message.chat_id, message_id=query.message.message_id, text=text)

def reject_reminder(query, context):
    booking_data = context.chat_data['booking_data']
    insert_booking(booking_data)
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
    selected_facility = query.data
    context.chat_data['selected_facility'] = selected_facility
    
    curr_time = int(datetime.now(pytz.timezone('Asia/Singapore')).strftime('%H'))
    timing_options = []
    start_time = 7 if curr_time < 7 else curr_time
    end_time = 23
    current = start_time
    
    booked_slots = get_booked_slots(context.chat_data['selected_facility'])
    while current <= end_time:
        if current in booked_slots:
            current += 1
            continue
        from_time = f'{current} AM' if current < 12 else ('12 PM' if current == 12 else f'{current - 12} PM')
        to_time = f'{current+1} AM' if current+1 < 12 else ('12 PM' if current+1 == 12 else f'{current+1 - 12} PM')
        timing_options.append([InlineKeyboardButton(f"{from_time} to {to_time}", callback_data=f"Session {current - 6}")])
        current += 1
    
    keyboard = timing_options
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    context.bot.edit_message_text(
        chat_id=query.message.chat_id,
        message_id=query.message.message_id,
        text="Select your timing",
        reply_markup=reply_markup
    )

def get_booked_slots(facility_selected):
    try:
        conn = mysql.connector.connect(
            host="localhost", 
            user="root",
            password="Password1!",
            database="ORCAChopes"
            )
        output = []
        if conn.is_connected():
            cursor = conn.cursor()
            cursor.execute("SELECT start_time FROM Bookings WHERE facility_name = %s", (facility_selected,))
            rows = cursor.fetchall()

            for row in rows:
                output.append(int(row[0].total_seconds() // 3600))
        return output

    except Error as e:
        print(f"Error inserting booking: {e}")

def confirm_booking(query, context):
    timing_selected = query.data
    start_time = get_session_info(timing_selected)[0]
    end_time = get_session_info(timing_selected)[1]
    context.chat_data['timing_selected'] = timing_selected
    response_text = f"{timing_selected} selected \nStart Time: {start_time} \nEnd Time: {end_time} \nConfirm booking?"
    keyboard = [[InlineKeyboardButton("Yes", callback_data='Accept Booking'),
                 InlineKeyboardButton("No", callback_data='Abort Booking')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    context.bot.send_message(chat_id=query.message.chat_id, text=response_text, reply_markup=reply_markup)

def insert_booking(booking_data):
    try:
        conn = mysql.connector.connect(
            host="localhost", 
            user="root",
            password="Password1!",
            database="ORCAChopes"
            )

        if conn.is_connected():
            cursor = conn.cursor()

            facility_name = booking_data['facility_name']
            username = booking_data['username']
            datetime = booking_data['datetime']
            start_time = booking_data['start_time']
            end_time = booking_data['end_time']
            cancelled = booking_data['cancelled']
            reminder = booking_data['reminder']
            firstname = booking_data['firstname']
            lastname = booking_data['lastname']
            date = booking_data['date']

            cursor.execute("SELECT username FROM Users WHERE username = %s", (username,))
            user_exists = cursor.fetchone()

            if not user_exists:
                cursor.execute("INSERT INTO Users (username, first_name, last_name) VALUES (%s, %s, %s)", (username, firstname, lastname))

            insert_query = """INSERT INTO Bookings (facility_name, username, datetime, date, start_time, end_time, cancelled, reminder)
                              VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""
            cursor.execute(insert_query, (facility_name, username, datetime, date, start_time, end_time, cancelled, reminder))
            conn.commit()

            print("Booking inserted successfully!")

    except Error as e:
        print(f"Error inserting booking: {e}")

def get_session_info(session):
    hour = int(session[8:]) + 6
    return (time(hour=hour), time(hour=hour+1))

def accept_booking(query, context):
    facility = context.chat_data['selected_facility']
    start_time = get_session_info(context.chat_data['timing_selected'])[0]
    end_time = get_session_info(context.chat_data['timing_selected'])[1]

    booking_data = {
    'facility_name': facility,
    'username': query.from_user.username,
    'firstname': query.from_user.first_name,
    'lastname': query.from_user.last_name,
    'datetime': datetime.now(pytz.timezone('Asia/Singapore')),
    'date': date.today(),
    'start_time': start_time,
    'end_time': end_time,
    'cancelled': False,
    'reminder': False
    }
    context.chat_data['booking_data'] = booking_data

    booking_text = f'Booking Confirmed! \nFacility: {facility} \nStart: {start_time} \nEnd: {end_time}'
    context.bot.send_message(chat_id=query.message.chat_id, text=booking_text)

    keyboard = [[InlineKeyboardButton("Yes", callback_data='Accept Reminder'),
                 InlineKeyboardButton("No", callback_data='Reject Reminder')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    context.bot.send_message(chat_id=query.message.chat_id, text="Would you like to set a reminder?", reply_markup=reply_markup)

def set_reminder(query, context):
    booking_data = context.chat_data['booking_data']
    booking_data['reminder'] = True
    insert_booking(booking_data)
    context.bot.edit_message_text(chat_id=query.message.chat_id, message_id=query.message.message_id, text="A reminder will be sent to you 15 minutes before the start time.")

if __name__ == '__main__':
    main()