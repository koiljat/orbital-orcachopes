import logging
from datetime import date, datetime, time, timedelta
import mysql.connector
from mysql.connector import Error
import pytz
import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, ConversationHandler, MessageHandler, Filters
from config import TOKEN

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                     level=logging.INFO)

#Connect to MySQL database -> Change password if needed
def connect_data_base():
    '''Establish connection to SQL database'''
    return mysql.connector.connect(
            host="localhost", 
            user="root",
            password="Password1!",
            database="ORCAChopes"
            )

#ConverstationHandlers States
ADVANCE_BOOKING = 0
COMMENT = 1

def main():
    #Setting up the bot
    bot = telegram.Bot(token=TOKEN)
    updater = Updater(TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    #Creating CommandHandlers
    start_handler = CommandHandler('start', start)
    quick_booking_handler = CommandHandler('quick_booking', quick_booking)
    check_bookings_handler = CommandHandler('check_bookings', check_bookings)
    advanced_booking_handler = CommandHandler('advanced_booking', advanced_booking)
    end_handler = CommandHandler('end', end)
    report_issue_handler = CommandHandler('report', report_issue)
    #Creating CallbackQueryHandlers
    button_handler = CallbackQueryHandler(button)
    #Creating ConversationHandlers
    conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(button),
            CommandHandler('report', report_issue)
            ],
        states={
            ADVANCE_BOOKING: [MessageHandler(Filters.all, select_timing_handler)],
            COMMENT: [MessageHandler(Filters.all, handle_report_comment)]
        },
        fallbacks=[]
    )

    #Add handlers to dispathcher
    dispatcher.add_handler(start_handler)
    dispatcher.add_handler(quick_booking_handler)
    dispatcher.add_handler(check_bookings_handler)
    dispatcher.add_handler(advanced_booking_handler)
    dispatcher.add_error_handler(report_issue_handler)
    dispatcher.add_handler(end_handler)
    dispatcher.add_handler(conv_handler)
    dispatcher.add_handler(button_handler)
    
    #Start running bot
    updater.start_polling()
    updater.idle()

def start(update, context):
    #Pull chat data
    get_chat_info(update, context)
    keyboard = [[InlineKeyboardButton("Quick Booking", callback_data='Quick Booking')],
                [InlineKeyboardButton("Check Booking", callback_data='Check Booking')],
                [InlineKeyboardButton("Advanced Booking", callback_data='Advance Booking')],
                [InlineKeyboardButton("Report Issue", callback_data='Report Issue')]
                ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = """
        Welcome to ORCAChopes, what would you like to do today?
        \nYou can operate the bot by sending these commands:
        \n/quick_booking - To book a slot for the day\n/check_bookings - To check you booked slot(s)\n/advance_booking - To book a slot up to 7 days in advance\n/report - To report any issues\n/end - To end the bot
        """
    context.bot.send_message(chat_id=update.effective_chat.id, text=text, reply_markup=reply_markup)

def end(update, context):
    '''End the bot immediately'''
    update.message.reply_text('Booking Terminated.')
    # Stop the updater (stop polling or webhook)
    context.dispatcher.stop()

def button(update, context):
    query = update.callback_query
    response = query.data

    facilities = ["Pool Table", "Mahjong Table",  "Foosball", "Darts"]

    query_actions = {
        "Confirm Booking": confirm_booking,
        "Accept Reminder": set_reminder,
        "Reject Reminder": reject_reminder,
        "Accept Booking": accept_booking,
        "Abort Booking": abort_booking,
        "Cancel Booking": handle_booking_selection
    }

    update_actions = {
        "Advance Booking": advanced_booking,
        "Check Booking": check_bookings,
        "Quick Booking": quick_booking,
        "Report Issue": report_issue,
        "handle_cancel_booking": handle_cancel_booking,
        "handle_done_booking": handle_done_booking
    }

    if response in query_actions:
        query_actions[response](query, context)
    elif response in update_actions:
        update_actions[response](update, context)
    elif response.find("Session") != -1:
        query_actions["Confirm Booking"](query, context)
    elif response.find("(Advance)") != -1:
        select_booking_dates(update, context)
    elif response in facilities:
        show_timing_options(query,context)
    elif response.isinstance(int):
        handle_booking_selection(update, context)
    elif response == "Select Time":
        context.bot.send_message(chat_id=update.effective_chat.id, 
            text="Please enter your booking timing in the following format: \nStart-End \nE.g. 1400-1530\n\nPlease only book intervals of 30 minutes")
        return ADVANCE_BOOKING
    else:
        context.bot.send_message(chat_id=query.message.chat_id, text="Unknown response!")

def get_chat_info(update, context):
    '''Saves the important chat data'''
    context.chat_data['username'] = update.effective_user.username
    context.chat_data['first_name'] = update.effective_user.first_name
    context.chat_data['last_name'] = update.effective_user.last_name
    context.chat_data['today_date'] = date.today()

def select_timing_handler(update, context):
    msg = update.message.text
    try:
        start_time, end_time = msg.split("-")
        context.chat_data['start_time'] = start_time
        context.chat_data['end_time'] = end_time
        response_text = f"{msg} selected \nStart Time: {start_time} \nEnd Time: {end_time} \nConfirm booking?"
        keyboard = [[
            InlineKeyboardButton("Yes", callback_data='Accept Booking'),
            InlineKeyboardButton("No", callback_data='Abort Booking')
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        context.bot.send_message(chat_id=update.effective_chat.id, text=response_text, reply_markup=reply_markup)
        return ConversationHandler.END

    except:
        update.message.reply_text("Invalid Input! \nPlease check your input and enter again: \n\nTo terminate booking, type /end")
        return ADVANCE_BOOKING

def advanced_booking(update, context):
    get_chat_info(update, context)
    keyboard = [[InlineKeyboardButton("Pool Table", callback_data='(Advance) Pool Table')],
                [InlineKeyboardButton("Mahjong Table", callback_data='(Advance) Mahjong Table')],
                [InlineKeyboardButton("Foosball", callback_data='(Advance) Foosball')],
                [InlineKeyboardButton("Darts", callback_data='(Advance) Darts')]
                ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)

    context.bot.send_message(chat_id=update.effective_chat.id, 
        text="Advance Booking selected. \nYou may book up to 7 days in advance. \nPlease select your facility:", 
        reply_markup=reply_markup)

def select_booking_dates(update, context):
    response = update.callback_query.data
    filler, facility = response.split(") ")
    context.chat_data['selected_facility'] = facility
    available_dates = get_available_dates()
    keyboard = []
    for date in available_dates:
        keyboard.append([InlineKeyboardButton(date, callback_data="Select Time")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    context.bot.send_message(chat_id=update.effective_chat.id, 
        text="Please select your date:",
        reply_markup=reply_markup)
    
def get_available_dates():
    today = datetime.now().date()
    end_date = today + timedelta(days=7) 
    date_list = []
    current_date = today
    while current_date < end_date:
        date_list.append(current_date)
        current_date += timedelta(days=1)
    date_string_list = [date.strftime('%Y-%m-%d') for date in date_list]
    return date_string_list

def report_issue(update, context):
    get_chat_info(update, context)
    print("Inside report_issue function")
    context.bot.send_message(chat_id=update.effective_chat.id, 
        text="Please provide your comment for the issue:")
    return COMMENT

def handle_report_comment(update, context):
    print("Inside handle_report_comment function")
    comment = update.message.text
    username = context.chat_data['username'] 
    current_datetime = datetime.now(pytz.timezone('Asia/Singapore'))
    try:
        conn = connect_data_base()
        if conn.is_connected():
            cursor = conn.cursor()
            sql_query = "INSERT INTO Reports (username, datetime, remarks) VALUES (%s, %s, %s)"
            cursor.execute(sql_query, (username, current_datetime, comment))
            conn.commit()
            update.message.reply_text("Your feedback has been submitted. Thank You.")
            print("Comment submitted successfully")
        else:
            update.message.reply_text("Oops! Something went wrong with the connection to the database. Please try again later.")
            print("Error: Could not connect to database")
    except Exception as e:
        update.message.reply_text("Oops! Something went wrong while handling your feedback. Please try again later.")
        print(str(e)) 
        
    return ConversationHandler.END

def cancel_report(update, context):
    context.chat_data.clear()
    update.message.reply_text("The report has been cancelled.")
    return ConversationHandler.END

def quick_booking(update, context):
    get_chat_info(update, context)
    keyboard = [[InlineKeyboardButton("Pool Table", callback_data='Pool Table')],
                [InlineKeyboardButton("Mahjong Table", callback_data='Mahjong Table')],
                [InlineKeyboardButton("Foosball", callback_data='Foosball')],
                [InlineKeyboardButton("Darts", callback_data='Darts')]
                ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "Select your facility:"
    if update.callback_query != None:
        context.bot.edit_message_text(chat_id=update.effective_chat.id, message_id=update.callback_query.message.message_id, text=text, reply_markup=reply_markup)
    else:
        context.bot.send_message(chat_id=update.effective_chat.id, text=text, reply_markup=reply_markup)

def convert_to_12h_format(time_delta):
    '''Convert time_delta object to 12h format'''
    total_seconds = time_delta.total_seconds()

    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)

    period = 'AM' if hours < 12 else 'PM'
    hours = hours % 12 or 12

    time_12h = f'{hours:02d}:{minutes:02d} {period}'

    return time_12h

def check_bookings(update, context):
    '''Show user their booked appointments'''
    get_chat_info(update, context)
    
    conn = connect_data_base()

    if conn.is_connected():
        cursor = conn.cursor()
        username = context.chat_data['username']
        
        sql_query = "SELECT booking_id, facility_name, date, start_time, end_time FROM bookings WHERE username = %s AND date = %s AND cancelled!= TRUE"
        cursor.execute(sql_query, (username, datetime.now().date()))

        booking_results = cursor.fetchall()
        booking_buttons = []

        for booking_id, facility_name, date, start_time, end_time in booking_results:
            start_time = convert_to_12h_format(start_time)
            end_time = convert_to_12h_format(end_time)
            context.chat_data['booking_id'] = booking_id
            booking_button= InlineKeyboardButton(
                    text = f"{facility_name} on {str(date)[5:]} from {start_time} to {end_time}",
                    callback_data = booking_id
                    )
            booking_buttons.append([booking_button])
        reply_markup = InlineKeyboardMarkup(booking_buttons)
        context.bot.send_message(chat_id=update.effective_chat.id, text="Select your Booking:", reply_markup=reply_markup)

def handle_booking_selection(update, context):
    query = update.callback_query
    context.chat_data['booking_id'] = query.data

    booking_options = [[
        InlineKeyboardButton("Cancel Booking", callback_data="handle_cancel_booking"), 
        InlineKeyboardButton("Done", callback_data="handle_done_booking")
    ]]

    conn = connect_data_base()

    if conn.is_connected():
        cursor = conn.cursor()
        booking_id = context.chat_data['booking_id']
        cursor.execute("SELECT facility_name, date, start_time, end_time FROM Bookings WHERE booking_id = %s AND cancelled = 0", (booking_id,))
        result = cursor.fetchone()

        reply_markup = InlineKeyboardMarkup(booking_options)
        query.message.reply_text("Select an option:", reply_markup=reply_markup)


def handle_cancel_booking(update, context):
    conn = connect_data_base()
    if conn.is_connected():
        cursor = conn.cursor()
        booking_id = context.chat_data['booking_id']
        sql_query = "UPDATE Bookings SET cancelled = TRUE WHERE booking_id = %s"
        cursor.execute(sql_query, (booking_id,))
        conn.commit()
        context.bot.send_message(chat_id=update.callback_query.message.chat_id, text=f"Booking ID {booking_id} canceled")
        #TO DO: implement a no booking message when current bookings are cancelled
        check_bookings(update, context)   

def handle_done_booking(update, context):
    query=update.callback_query
    booking_id = query.data.split("_")[1]
    query.message.reply_text(f"booking {booking_id} confirmed")

def abort_booking(query, context):
    text = "Booking terminated. \nThank you for using ORCAChopes."
    context.bot.edit_message_text(chat_id=query.message.chat_id, message_id=query.message.message_id, text=text)

def reject_reminder(query, context):
    booking_data = context.chat_data['booking_data']
    insert_booking(booking_data)
    text = "Thank you for booking! \nPlease remember to cancel your booking if you are not able to make it for the session."
    context.bot.edit_message_text(chat_id=query.message.chat_id, message_id=query.message.message_id, text=text)

def show_timing_options(query, context):
    selected_facility = query.data
    context.chat_data['selected_facility'] = selected_facility
    
    curr_time = int(datetime.now(pytz.timezone('Asia/Singapore')).strftime('%H'))
    timing_options = []
    start_time = 7 if curr_time < 7 else curr_time
    end_time = 22
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
        text=f"{selected_facility} selected. \nPlease select your timing",
        reply_markup=reply_markup
    )

def get_booked_slots(facility_selected):
    try:
        conn = connect_data_base()
        output = []
        if conn.is_connected():
            cursor = conn.cursor()
            cursor.execute("SELECT start_time FROM Bookings WHERE facility_name = %s AND cancelled = 0", (facility_selected,))
            rows = cursor.fetchall()

            for row in rows:
                output.append(int(row[0].total_seconds() // 3600))
        return output

    except Error as e:
        print(f"Error inserting booking: {e}")

def confirm_booking(query, context):
    timing_selected = query.data
    start_time = get_session_info(timing_selected)[0]
    context.chat_data['start_time'] = start_time
    end_time = get_session_info(timing_selected)[1]
    context.chat_data['end_time'] = end_time

    response_text = f"{timing_selected} selected \nStart Time: {start_time} \nEnd Time: {end_time} \nConfirm booking?"

    keyboard = [[InlineKeyboardButton("Yes", callback_data='Accept Booking'),
                 InlineKeyboardButton("No", callback_data='Abort Booking')]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    context.bot.edit_message_text(
        chat_id=query.message.chat_id, 
        message_id=query.message.message_id, 
        text=response_text, 
        reply_markup=reply_markup)

def insert_booking(booking_data):
    try:
        conn = connect_data_base()

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
    start_time = context.chat_data['start_time']
    end_time = context.chat_data['end_time']

    booking_data = {
    'facility_name': facility,
    'username': context.chat_data['username'],
    'firstname': context.chat_data['first_name'],
    'lastname': context.chat_data['last_name'],
    'datetime': datetime.now(pytz.timezone('Asia/Singapore')),
    'date': date.today(),
    'start_time': start_time,
    'end_time': end_time,
    'cancelled': False,
    'reminder': False
    }
    context.chat_data['booking_data'] = booking_data

    booking_text = f'Booking Confirmed! \nFacility: {facility} \nStart: {start_time} \nEnd: {end_time}'

    keyboard = [[InlineKeyboardButton("Yes", callback_data='Accept Reminder'),
                 InlineKeyboardButton("No", callback_data='Reject Reminder')]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    context.bot.edit_message_text(
        chat_id=query.message.chat_id, 
        message_id=query.message.message_id, 
        text=booking_text
        )
    
    context.bot.send_message(chat_id=query.message.chat_id, text="Would you like to set a reminder?", reply_markup=reply_markup)

def set_reminder(query, context):
    booking_data = context.chat_data['booking_data']
    booking_data['reminder'] = True
    insert_booking(booking_data)
    context.bot.edit_message_text(chat_id=query.message.chat_id, message_id=query.message.message_id, text="A reminder will be sent to you 15 minutes before the start time.")

if __name__ == '__main__':
    main()