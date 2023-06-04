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
STATE_COMMENT = 1
                                
def main():
    #Setting up the bot
    bot = telegram.Bot(token=TOKEN)
    updater = Updater(TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    #Creating CommandHandlers
    start_handler = CommandHandler('start', start)
    quick_booking_handler = CommandHandler('quick_booking', quick_booking)
    check_bookings_handler = CommandHandler('check_bookings', check_bookings)
    advanced_booking_handler = CommandHandler('advance_booking', advanced_booking)
    end_handler = CommandHandler('end', end)
    report_issue_handler = CommandHandler('report', report_issue)

    #Creating CallbackQueryHandlers
    button_handler = CallbackQueryHandler(button)

    #Creating ConversationHandlers
    conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(button),
            report_issue_handler
            ],
        states={
            ADVANCE_BOOKING: [MessageHandler(Filters.all, get_custom_timing)],
            STATE_COMMENT: [MessageHandler(Filters.all, handle_report_comment)]
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

### General Bot Functions ###
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

    if update.callback_query != None:
        context.bot.edit_message_text(
            chat_id=update.effective_chat.id, 
            message_id=update.callback_query.message.message_id, 
            text=text, 
            reply_markup=reply_markup
            )
    else:
        context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text=text, 
            reply_markup=reply_markup
            )

def end(update, context):
    '''End the bot immediately'''
    update.message.reply_text('ORCAChopes Bot has stopped. Use /start to restart.')
    return ConversationHandler.END

def button(update, context):
    '''Callback data handler'''
    #TODO: Need to clean up the dictionary and mapping
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
        "handle_cancel_booking": handle_cancel_booking,
        "handle_done_booking": handle_done_booking,
        "handle_booking_selection": handle_booking_selection,
        "start": start,
        "cancel_booking": cancel_booking
    }

    if response in query_actions:
        query_actions[response](query, context)
    elif response in update_actions:
        update_actions[response](update, context)
    elif response.isdigit():
        handle_booking_selection(update, context)
    elif response.find("Session") != -1:
        query_actions["Confirm Booking"](query, context)
    elif response.find("(Advance)") != -1:
        show_booking_dates(update, context)
        return ConversationHandler.END
    elif response in facilities:
        show_available_time(query,context)
    elif response == "Report Issue":
        report_issue(update, context)
        return STATE_COMMENT
    elif response == "Select Time":
        context.bot.edit_message_text(
            chat_id=update.effective_chat.id, 
            message_id=update.callback_query.message.message_id, 
            text="Please enter your booking timing in the following format: \n\nStart-End \nE.g. 1400-1530\n\nPlease only book intervals of 30 minutes",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('Back', callback_data=f"(Advance) {context.chat_data['selected_facility']}")]])
            )
        return ADVANCE_BOOKING
    else:
        print(response)
        context.bot.send_message(chat_id=query.message.chat_id, text="Unknown response!")

def get_chat_info(update, context):
    '''Saves the important chat data'''
    context.chat_data['username'] = update.effective_user.username
    context.chat_data['first_name'] = update.effective_user.first_name
    context.chat_data['last_name'] = update.effective_user.last_name
    context.chat_data['today_date'] = date.today()

### ADVANCE BOOKING ###
def advanced_booking(update, context):
    '''Command Hanlder for Advance Booking Feature'''
    get_chat_info(update, context)

    keyboard = [[InlineKeyboardButton("Back", callback_data='start')],
                [InlineKeyboardButton("Pool Table", callback_data='(Advance) Pool Table')],
                [InlineKeyboardButton("Mahjong Table", callback_data='(Advance) Mahjong Table')],
                [InlineKeyboardButton("Foosball", callback_data='(Advance) Foosball')],
                [InlineKeyboardButton("Darts", callback_data='(Advance) Darts')]
                ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = "Advance Booking selected. \nYou may book up to 7 days in advance. \nPlease select your facility:"

    if update.callback_query != None:
        context.bot.edit_message_text(
            chat_id=update.effective_chat.id, 
            message_id=update.callback_query.message.message_id, 
            text=text, 
            reply_markup=reply_markup
            )
    else:
        context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text=text, 
            reply_markup=reply_markup
            )

def show_booking_dates(update, context):
    '''Allows user to select the immediate 7 days for booking.'''
    response = update.callback_query.data

    #Get the facility
    facility = response.split(") ")[1]

    #Saves the selected facility
    context.chat_data['selected_facility'] = facility

    #Get the available dates
    available_dates = get_advance_booking_dates()
    keyboard = [[InlineKeyboardButton("Back", callback_data="Advance Booking")]]

    #Create the InLineKeyboardButton Object for each date
    for date in available_dates:
        keyboard.append([InlineKeyboardButton(date, callback_data="Select Time")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)

    context.bot.edit_message_text(
        chat_id=update.effective_chat.id, 
        message_id=update.callback_query.message.message_id, 
        text="Please select your date:", 
        reply_markup=reply_markup
        )

def get_custom_timing(update, context):
    '''Allows user to enter their custom booking timing'''
    user_input = update.message.text

    #This is to exit the conversation when user wants to forcefully terminate session.
    if user_input == '/end':
        end(update, context)
    try:
        start_time, end_time = user_input.split("-")
        if validate_user_input(start_time, end_time):
            #Converts the user_input time to datetime object
            start_time = datetime.strptime(start_time, '%H%M').time()
            end_time = datetime.strptime(end_time, '%H%M').time()

            #Saves the start_time and end_time for insertion later
            context.chat_data['start_time'] = start_time
            context.chat_data['end_time'] = end_time

            response_text = f"{context.chat_data['selected_facility']} selected \nStart Time: {start_time} \nEnd Time: {end_time} \nConfirm booking?"

            keyboard = [
                [InlineKeyboardButton("Yes", callback_data='Accept Booking'), InlineKeyboardButton("No", callback_data='Abort Booking')],
                [InlineKeyboardButton("Back", callback_data="Select Time")]
                ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            context.bot.send_message(
                chat_id=update.effective_chat.id, 
                text=response_text, 
                reply_markup=reply_markup
                )

            return ConversationHandler.END
        else:
            raise Exception("Invalid Input!")
    except:
        update.message.reply_text("Invalid Input! \nPlease check your input and enter again: \n\nTo terminate booking, type /end")
        return ADVANCE_BOOKING

def validate_user_input(start_time_str, end_time_str):
    try:
        start_time = datetime.strptime(start_time_str, '%H%M')
        end_time = datetime.strptime(end_time_str, '%H%M')

        if start_time >= end_time:
            return False

        if start_time.minute % 30 != 0 or end_time.minute % 30 != 0:
            return False
    
        return True
    except ValueError:
        return False

def get_advance_booking_dates():
    '''Get dates available for advance booking'''
    #Get the current date
    today = datetime.now().date()
    end_date = today + timedelta(days=7) 
    date_list = []
    current_date = today

    #Create a list of dates
    while current_date < end_date:
        date_list.append(current_date)
        current_date += timedelta(days=1)

    date_string_list = [date.strftime('%Y-%m-%d') for date in date_list]

    return date_string_list

#TODO: Show the currently available booking time
#TODO: Disallow users to advance book already booked timing
def fetch_advance_booking_availability(update, context):
    '''Fetches the availability of the facility'''

    min_available_time = 730
    max_available_time = 2330
    available_time = []

    conn = connect_data_base()
    if conn.is_connected():
            cursor = conn.cursor()
            cursor.execute("SELECT start_time, end_time FROM Bookings WHERE facility_name = %s AND cancelled = 0 AND date = %s", 
                (context.chat_data['selected_facility'], context.chat_data['date']))
            rows = cursor.fetchall()
    
    pass
    
### REPORT/FEEDBACK/COMPLAIN ###    
def report_issue(update, context): 
    '''Command Handler for Report Issue Feature'''
    get_chat_info(update, context)

    keyboard = [[InlineKeyboardButton("Back", callback_data='start')]]

    reply_markup = InlineKeyboardMarkup(keyboard)

    text = "Please provide your comment for the issue:"

    if update.callback_query != None:
        context.bot.edit_message_text(
            chat_id=update.effective_chat.id, 
            message_id=update.callback_query.message.message_id, 
            text=text, 
            reply_markup=reply_markup
            )
        return STATE_COMMENT
    else:
        context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text=text, 
            reply_markup=reply_markup
            )
        return STATE_COMMENT
    
def handle_report_comment(update, context):
    '''Handles the STATE_COMMENT for the report issue feature'''
    STATE_COMMENT = update.message.text
    if STATE_COMMENT == "/report":
        raise Exception("Invalid!")
    username = context.chat_data['username'] 
    current_datetime = datetime.now(pytz.timezone('Asia/Singapore'))
    try:
        conn = connect_data_base()
        if conn.is_connected():
            cursor = conn.cursor()
            sql_query = "INSERT INTO Reports (username, datetime, remarks) VALUES (%s, %s, %s)"
            cursor.execute(sql_query, (username, current_datetime, STATE_COMMENT))
            conn.commit()
            update.message.reply_text("Your feedback has been submitted. Thank You.")
            print("STATE_COMMENT submitted successfully")
        else:
            update.message.reply_text("Oops! Something went wrong with the connection to the database. Please try again later.")
            print("Error: Could not connect to database")
    except Exception as e:
        update.message.reply_text("Oops! Something went wrong while handling your feedback. Please try again later.")
        print(str(e)) 
        
    return ConversationHandler.END

def terminate_report(update, context):
    '''Terminate report'''
    context.chat_data.clear()
    update.message.reply_text("The report has been cancelled.")
    return ConversationHandler.END

### QUICK BOOKING ###
def quick_booking(update, context):
    '''Command Handler for Quick Booking Feature'''
    get_chat_info(update, context)

    keyboard = [[InlineKeyboardButton("Back", callback_data='start')],
                [InlineKeyboardButton("Pool Table", callback_data='Pool Table')],
                [InlineKeyboardButton("Mahjong Table", callback_data='Mahjong Table')],
                [InlineKeyboardButton("Foosball", callback_data='Foosball')],
                [InlineKeyboardButton("Darts", callback_data='Darts')]
                ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "Select your facility:"

    if update.callback_query != None:
        context.bot.edit_message_text(
            chat_id=update.effective_chat.id, 
            message_id=update.callback_query.message.message_id, 
            text=text, 
            reply_markup=reply_markup
            )
    else:
        context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text=text, 
            reply_markup=reply_markup
            )

def show_available_time(query, context):
    selected_facility = query.data
    context.chat_data['selected_facility'] = selected_facility
    
    curr_time = int(datetime.now(pytz.timezone('Asia/Singapore')).strftime('%H'))
    timing_options = [[InlineKeyboardButton("Back", callback_data="Quick Booking")]]

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

def convert_to_12h_format(time_delta):
    '''Convert time_delta object to 12h format'''
    total_seconds = time_delta.total_seconds()

    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)

    period = 'AM' if hours < 12 else 'PM'
    hours = hours % 12 or 12

    time_12h = f'{hours:02d}:{minutes:02d} {period}'

    return time_12h

def get_session_info(session):
    hour = int(session[8:]) + 6
    return (time(hour=hour), time(hour=hour+1))

### CHECK BOOKING ###
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
        booking_buttons = [[InlineKeyboardButton("Back", callback_data='start')]]

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
        text="Select your Booking:"

        if update.callback_query != None:
            context.bot.edit_message_text(
                chat_id=update.effective_chat.id, 
                message_id=update.callback_query.message.message_id, 
                text=text, 
                reply_markup=reply_markup
                )
        else:
            context.bot.send_message(
                chat_id=update.effective_chat.id, 
                text=text, 
                reply_markup=reply_markup
                )

def handle_booking_selection(update, context):
    context.chat_data['booking_id'] = update.callback_query.data

    booking_options = [[
        InlineKeyboardButton("Cancel Booking", callback_data="handle_cancel_booking"), 
        InlineKeyboardButton("Done", callback_data="handle_done_booking")
        ],
        [InlineKeyboardButton("Back", callback_data="Check Booking")]]
        
    booking_result = get_booking_details(update.callback_query.data)
    text = f"""Facility: {booking_result[0]}\nDate: {booking_result[1]}\nStart Time: {booking_result[2]}\nEnd Time: {booking_result[3]}\n\nSelect an option:"""

    reply_markup = InlineKeyboardMarkup(booking_options)

    context.bot.edit_message_text(
        chat_id=update.effective_chat.id, 
        message_id=update.callback_query.message.message_id, 
        text=text,
        reply_markup=reply_markup
        )
        
def get_booking_details(booking_id):
    conn = connect_data_base()

    if conn.is_connected():
        cursor = conn.cursor()
        sql_query = "SELECT facility_name, date, start_time, end_time FROM Bookings WHERE booking_id = %s"
        cursor.execute(sql_query, (booking_id,))
        booking_result = cursor.fetchone()
        print(booking_result)
        return booking_result

def handle_cancel_booking(update, context):
    booking_id = context.chat_data['booking_id']
    booking_result = get_booking_details(booking_id)

    keyboard = [[InlineKeyboardButton("Yes", callback_data="cancel_booking")],
                [InlineKeyboardButton("Back", callback_data=booking_id)]]

    reply_markup = InlineKeyboardMarkup(keyboard)

    text = f"""Facility: {booking_result[0]}\nDate: {booking_result[1]}\nStart Time: {booking_result[2]}\nEnd Time: {booking_result[3]}\n\nAre you sure you want to cancel?
        """
    context.bot.edit_message_text(
        chat_id=update.effective_chat.id, 
        message_id=update.callback_query.message.message_id, 
        text=text,
        reply_markup=reply_markup
        )

def cancel_booking(update, context):
    conn = connect_data_base()
    
    if conn.is_connected():
        booking_id = context.chat_data['booking_id']
        cursor = conn.cursor()
        booking_id = context.chat_data['booking_id']
        sql_query = "UPDATE Bookings SET cancelled = TRUE WHERE booking_id = %s"
        cursor.execute(sql_query, (booking_id,))
        conn.commit()
        
        text = "Booking cancelled. To make another booking, enter /quick_booking or /advance_booking"

        context.bot.edit_message_text(
            chat_id=update.effective_chat.id, 
            message_id=update.callback_query.message.message_id, 
            text=text
        )

def handle_done_booking(update, context):
    query = update.callback_query

    text = "Thank you for using ORCAChopes Have a nice day!"

    context.bot.edit_message_text(
        chat_id=query.message.chat_id, 
        message_id=query.message.message_id, 
        text=text
        )

### General Booking Functions ###
def abort_booking(query, context):
    text = "Booking terminated. \nThank you for using ORCAChopes.\n To make another booking, enter /quick_booking or /advance_booking"

    context.bot.edit_message_text(
        chat_id=query.message.chat_id, 
        message_id=query.message.message_id, 
        text=text
        )

def get_booked_slots(facility_selected):
    conn = connect_data_base()
    output = []
    if conn.is_connected():
        cursor = conn.cursor()
        cursor.execute("SELECT start_time FROM Bookings WHERE facility_name = %s AND cancelled = 0", (facility_selected,))
        rows = cursor.fetchall()
        for start_time in rows:
            output.append(int(start_time.total_seconds() // 3600))
    return output

def confirm_booking(query, context):
    timing_selected = query.data
    start_time = get_session_info(timing_selected)[0]
    end_time = get_session_info(timing_selected)[1]
    context.chat_data['end_time'] = end_time
    context.chat_data['start_time'] = start_time

    response_text = f"{context.chat_data['selected_facility']} \nStart: {start_time} \nEnd: {end_time} \nConfirm booking?"

    keyboard = [[
        InlineKeyboardButton("Yes", callback_data='Accept Booking'),
        InlineKeyboardButton("No", callback_data='Abort Booking')
        ],
        [InlineKeyboardButton("Back", callback_data=context.chat_data['selected_facility'])]
        ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    context.bot.edit_message_text(
        chat_id=query.message.chat_id, 
        message_id=query.message.message_id, 
        text=response_text, 
        reply_markup=reply_markup
        )

def insert_booking(booking_data):
    '''Insert the booking data'''
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

    text = f'Booking Confirmed! \nFacility: {facility} \nStart: {start_time} \nEnd: {end_time}'

    keyboard = [[
        InlineKeyboardButton("Yes", callback_data='Accept Reminder'),
        InlineKeyboardButton("No", callback_data='Reject Reminder')
        ]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    context.bot.edit_message_text(
        chat_id=query.message.chat_id, 
        message_id=query.message.message_id, 
        text=text
        )
    
    context.bot.send_message(
        chat_id=query.message.chat_id, 
        text="Would you like to set a reminder?", 
        reply_markup=reply_markup
        )

### REMINDER FUNCTIONS ###
#TODO: Set up working reminder features
def set_reminder(query, context):
    booking_data = context.chat_data['booking_data']
    booking_data['reminder'] = True

    insert_booking(booking_data)

    text = "A reminder will be sent to you 15 minutes before the start time.\n\nTo make another booking, enter /quick_booking or /advance_booking"

    context.bot.edit_message_text(
        chat_id=query.message.chat_id, 
        message_id=query.message.message_id, 
        text=text)

def reject_reminder(query, context):
    booking_data = context.chat_data['booking_data']

    insert_booking(booking_data)

    text = "Thank you for booking! \nPlease remember to cancel your booking if you are not able to make it for the session.\n\nTo make another booking, enter /quick_booking or /advance_booking"

    context.bot.edit_message_text(
        chat_id=query.message.chat_id, 
        message_id=query.message.message_id, 
        text=text)

if __name__ == '__main__':
    main()

    