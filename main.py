from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, ConversationHandler, MessageHandler, Filters
from datetime import date, datetime
from config import *
from helper import *
import pytz

### ConversationHandler States
ADVANCE_BOOKING = 0
STATE_COMMENT = 1

def main():
    '''This is used to set up the neccesary for the bot'''

    #Create the bot
    bot = Bot(token=TOKEN) #We will import the TOKEN from the config.py file

    #Create dispatcher to register handlers
    updater = Updater(TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    #Create CommandHandler objects for functions
    start_handler = CommandHandler('start', start, pass_args=True)
    quick_booking_handler = CommandHandler('quick_booking', quick_booking)
    check_bookings_handler = CommandHandler('check_bookings', check_bookings)
    advanced_booking_handler = CommandHandler('advance_booking', advanced_booking)
    report_issue_handler = CommandHandler('report', report_issue)
    end_handler = CommandHandler('end', end)
    instant_booking_handler= CommandHandler('instant_booking', instant_booking)
    #Create CallbackQueryHandlers
    query_handler = CallbackQueryHandler(handle_query)

    #Creating ConversationHandlers
    conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(handle_query),
            report_issue_handler
            ],
        states={
            ADVANCE_BOOKING: [MessageHandler(Filters.all, get_user_timing)],
            STATE_COMMENT: [MessageHandler(Filters.all, handle_report_comment)]
            },
        fallbacks=[]
    )

    #Register handlers
    dispatcher.add_handler(conv_handler)
    dispatcher.add_handler(start_handler)
    dispatcher.add_handler(quick_booking_handler)
    dispatcher.add_handler(check_bookings_handler)
    dispatcher.add_handler(advanced_booking_handler)
    dispatcher.add_handler(report_issue_handler)
    dispatcher.add_handler(end_handler)
    dispatcher.add_handler(query_handler)
    dispatcher.add_handler(instant_booking_handler)

    #Run the bot
    updater.start_polling()
    updater.idle() #This keeps the bot alert for incoming updates

def start(update, context):
    '''This function will start the bot and provide an interface for users to nagivate.'''
    #Collect user data
    get_user_details(update, context)

    #check if any facillity is passed as an argument via the qrcode
    args = context.args
    if args:
        facility = args[0].replace('_', ' ').title()
        instant_booking(update, context, facility)
        return

    #Create an InlineKeyboard for user to interact
    keyboard = [[InlineKeyboardButton("Quick Booking", callback_data='Quick Booking')],
    [InlineKeyboardButton("Check Booking", callback_data='Check Booking')],
    [InlineKeyboardButton("Advanced Booking", callback_data='Advance Booking')],
    [InlineKeyboardButton("Report Issue", callback_data='Report Issue')]]

    reply_markup = InlineKeyboardMarkup(keyboard)

    text = """
        Welcome to ORCAChopes, what would you like to do today?
        \nYou can operate the bot by sending these commands:
        \n/quick_booking - To book a slot for the day\n/check_bookings - To check you booked slot(s)\n/advance_booking - To book a slot up to 7 days in advance\n/report - To report any issues\n/end - To end the bot
        """
    
    send_message(update, context, text, reply_markup) #We will abstract this since we will be using it multiple times later.

def end(update  , context):
    # Clear any ongoing conversations or active handlers
    context.dispatcher.clear_conversations()
    context.job_queue.stop()
    
    # Send a farewell message to the user
    context.bot.send_message(chat_id=update.effective_chat.id, text="Terminating...\nThanks for using ORCAChopes!")

def send_message(update, context, text, reply_markup):
    if update.callback_query != None: 
        #This is to refine the interface for backward navigation. Avoid flooding the bot with messages.
        context.bot.edit_message_text(chat_id=update.effective_chat.id, 
            message_id=update.callback_query.message.message_id, 
            text=text, 
            reply_markup=reply_markup)
    else:
        context.bot.send_message(chat_id=update.effective_chat.id, 
            text=text, 
            reply_markup=reply_markup)

def get_user_details(update, context):
    '''This function will collect the user data and saves them in context.chat_data.'''
    context.chat_data['username'] = update.effective_user.username
    context.chat_data['first_name'] = update.effective_user.first_name
    context.chat_data['last_name'] = update.effective_user.last_name
    context.chat_data['today_date'] = date.today()
 
### CallbackQueryHandler
def handle_query(update, context):
    '''This function will tell the bot what is the next action.'''
    query = update.callback_query
    response = query.data
    
    function_dict = {
        'Quick Booking': quick_booking,
        'Check Booking': check_bookings,
        'Advance Booking': advanced_booking,
        'Back': start,
        'Instant Booking': instant_booking,
        'Pool Table': select_quick_booking_timing,
        'Mahjong Table': select_quick_booking_timing,
        'Foosball': select_quick_booking_timing,
        'Darts': select_quick_booking_timing,
        'Book': handle_instant_booking,
        'Confirm Booking': confirm_booking,
        'Accept Booking': accept_booking,
        "Abort Booking": abort_booking,
        "Accept Reminder": set_reminder,
        "Reject Reminder": reject_reminder,
        'Cancel Booking': handle_cancel_booking,
        'Confirm Cancel': cancel_booking,
        'Done': handle_done_booking
    }

    if response in function_dict:
        function_dict[response](update, context)
    elif response.find("Session") != -1:
        confirm_booking(update, context)
    elif response.isdigit():
        handle_selected_booking(update, context)
    elif response.find("(Advance)") != -1:
        show_booking_dates(update, context)
        return ConversationHandler.END
    elif response.split(',')[0] == "Select Time":
        context.chat_data['selected_date'] = response.split(',')[1]
        context.chat_data['previous'] = f"Select Time, {context.chat_data['selected_date']}"
        context.bot.edit_message_text(chat_id=update.effective_chat.id, 
            message_id=update.callback_query.message.message_id, 
            text=f"Please enter your booking timing in the following format: \n\nStart-End \nE.g. 1400-1530\n\nPlease only book intervals of 30 minutes.\nAvailable Timings:\n{get_available_timings(context.chat_data['selected_date'],context.chat_data['selected_facility'])} ",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('Back', callback_data=f"(Advance) {context.chat_data['selected_facility']}")]]))
        return ADVANCE_BOOKING
    elif response == "Report Issue":
        report_issue(update, context)
    else:
        context.bot.send_message(chat_id=query.message.chat_id, text="Unknown response!")

#### Quick Booking Feature
def quick_booking(update, context):
    '''This will allow user to book a facility on the day.'''
    get_user_details(update, context) #We need to collect user details, just in case function not triggered via start

    keyboard = [[InlineKeyboardButton("Back", callback_data='Back')],
    [InlineKeyboardButton("Pool Table", callback_data='Pool Table')],
    [InlineKeyboardButton("Mahjong Table", callback_data='Mahjong Table')],
    [InlineKeyboardButton("Foosball", callback_data='Foosball')],
    [InlineKeyboardButton("Darts", callback_data='Darts')]]

    reply_markup = InlineKeyboardMarkup(keyboard)

    text = "Select your facility:"

    send_message(update, context, text, reply_markup)

def select_quick_booking_timing(update, context):
    '''This function will show the timings available for quick booking.'''
    #Saves the facility selected
    
    selected_facility = update.callback_query.data
    context.chat_data['selected_facility'] = selected_facility
    context.chat_data['previous'] = selected_facility
    context.chat_data['selected_date'] = date.today()

    keyboard = [[InlineKeyboardButton("Back", callback_data="Quick Booking")]]

    current_slot = int(datetime.now().strftime("%H"))
    booked_slots = get_booked_slots(selected_facility, context.chat_data['today_date'])
    occupied_hours = []
    for slot in booked_slots:
        start = int(str(slot[0]).split(':')[0])
        end = int(str(slot[1]).split(':')[0])
        if int(str(slot[1]).split(':')[1]):
            end += 1
        occupied_hours.extend(list(range(start,end)))
    booked_slots = occupied_hours
    first_slot = 7 if current_slot < 7 else current_slot 
    last_slot = 22
    current_slot = first_slot
    current_slot = 7
    while current_slot <= last_slot:
        if current_slot in booked_slots:
            current_slot += 1
            continue
        start_time = convert_to_12_hour_format(current_slot)
        end_time = convert_to_12_hour_format(current_slot + 1)
        current_slot += 1
        keyboard.append([InlineKeyboardButton(f"{start_time} to {end_time}", callback_data=f"Session {current_slot - 7}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = f"{selected_facility} selected.\n\nPlease select your timing"

    context.bot.edit_message_text(chat_id=update.effective_chat.id, 
        message_id=update.callback_query.message.message_id, 
        text=text, 
        reply_markup=reply_markup)

def get_booked_slots(facility, date):
    '''This function will return a list of booked slots for the facility on the date.'''
    with connect_to_sql() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT start_time, end_time FROM Bookings WHERE facility_name = %s AND cancelled = 0 AND date = %s", (facility, date))
        booked_slots = cursor.fetchall()
        return booked_slots

### General Functions
def confirm_booking(update, context):
    '''This function will check with user if user wants to book the selected slot'''
    query = update.callback_query
    session_selected = query.data
    if session_selected.find("Session") != -1:
        start_time = get_session_info(session_selected)[0]
        end_time = get_session_info(session_selected)[1]
    context.chat_data['end_time'] = end_time
    context.chat_data['start_time'] = start_time

    response_text = f"{context.chat_data['selected_facility']} selected\nDate: {context.chat_data['today_date']}\nStart: {start_time} \nEnd: {end_time} \nConfirm booking?"

    keyboard = [[InlineKeyboardButton("Yes", callback_data='Accept Booking'),InlineKeyboardButton("No", callback_data='Abort Booking')],
        [InlineKeyboardButton("Back", callback_data=context.chat_data['selected_facility'])]]

    reply_markup = InlineKeyboardMarkup(keyboard)

    context.bot.edit_message_text(chat_id=query.message.chat_id, 
    message_id=query.message.message_id, 
    text=response_text, 
    reply_markup=reply_markup)

def accept_booking(update, context):
    '''This function will send user a booking confirmed message.'''
    facility = context.chat_data['selected_facility']
    start_time = context.chat_data['start_time']
    end_time = context.chat_data['end_time']
    date = context.chat_data['selected_date']

    booking_data = {
        'facility_name': context.chat_data['selected_facility'],
        'username': context.chat_data['username'],
        'firstname': context.chat_data['first_name'],
        'lastname': context.chat_data['last_name'],
        'datetime': datetime.now(),
        'date': context.chat_data['selected_date'],
        'start_time': context.chat_data['start_time'],
        'end_time': context.chat_data['end_time'],
        'cancelled': False,
        'reminder': False
        }

    context.chat_data['booking_data'] = booking_data

    text = f'Booking Confirmed!\nDate: {date} \nFacility: {facility} \nStart: {start_time} \nEnd: {end_time}'

    keyboard = [[InlineKeyboardButton("Yes", callback_data='Accept Reminder'),
        InlineKeyboardButton("No", callback_data='Reject Reminder')]]

    reply_markup = InlineKeyboardMarkup(keyboard)

    context.bot.edit_message_text(chat_id=update.effective_chat.id, 
        message_id=update.callback_query.message.message_id, 
        text=text)
    
    context.bot.send_message(chat_id=update.effective_chat.id, 
            text="Would you like to set a reminder?", 
            reply_markup=reply_markup)

def abort_booking(update, context):
    '''This function will quit booking.'''

    text = "Booking terminated. \nThank you for using ORCAChopes.\n To make another booking, enter /quick_booking or /advance_booking"

    context.bot.edit_message_text(chat_id=update.effective_chat.id, 
        message_id=update.callback_query.message.message_id, 
        text=text)

def insert_booking(booking_data):
    '''This function helps to insert the booking data into MySQL database.'''
    with connect_to_sql() as conn:
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

        cursor.execute("SELECT * FROM Bookings WHERE start_time = %s AND end_time = %s AND facility_name = %s AND date = %s",
            (start_time, end_time, facility_name, date))

        if cursor.fetchall():
            raise Exception("Error. Please try again.")

        cursor.execute(insert_query, (facility_name, username, datetime, date, start_time, end_time, cancelled, reminder))
        conn.commit()

#TODO: Set up working reminder features
def set_reminder(update, context):
    booking_data = context.chat_data['booking_data']
    booking_data['reminder'] = True
    try:
        insert_booking(booking_data)
    except Exception as e:
        context.bot.edit_message_text(chat_id=update.effective_chat.id, 
            message_id=update.callback_query.message.message_id, 
            text=str(e))
    else:
        text = "A reminder will be sent to you 15 minutes before the start time.\n\nTo make another booking, enter /quick_booking or /advance_booking"
        context.bot.edit_message_text(chat_id=update.effective_chat.id, 
            message_id=update.callback_query.message.message_id, 
            text=text)

def reject_reminder(update, context):
    booking_data = context.chat_data['booking_data']
    try:
        insert_booking(booking_data)
    except Exception as e:
        context.bot.edit_message_text(chat_id=update.effective_chat.id, 
            message_id=update.callback_query.message.message_id, 
            text=str(e))
    else:
        text = "Thank you for booking! \nPlease remember to cancel your booking if you are not able to make it for the session.\n\nTo make another booking, enter /quick_booking or /advance_booking"
        context.bot.edit_message_text(chat_id=update.effective_chat.id, 
            message_id=update.callback_query.message.message_id, 
            text=text)

    booking_data = context.chat_data['booking_data']
    try:
        insert_booking(booking_data)
    except Exception as e:
        context.bot.edit_message_text(chat_id=update.effective_chat.id, 
            message_id=update.callback_query.message.message_id, 
            text=str(e))
    else:
        text = "Thank you for booking! \nPlease remember to cancel your booking if you are not able to make it for the session.\n\nTo make another booking, enter /quick_booking or /advance_booking"
        context.bot.edit_message_text(chat_id=update.effective_chat.id, 
            message_id=update.callback_query.message.message_id, 
            text=text)
        
### Instant Booking Feature
def instant_booking(update, context, facility):
    get_user_details(update, context)
    '''This function will allow the user to book the facility within the current hour'''

    curr_time = datetime.now(pytz.timezone('Asia/Singapore'))
    curr_date = context.chat_data['today_date']
    
    context.chat_data['selected_facility']=facility
    context.chat_data['selected_date'] = date.today()
    context.chat_data['start_time']= curr_time.replace(minute=0, second=0)
    context.chat_data['end_time']= context.chat_data['start_time']+ timedelta(hours=1)

    if facility is None:
        context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text="No facility specified."
        )
        return
    
    booked=check_currently_booked(curr_date, curr_time, facility)
    
    if not booked:
        keyboard = [
            [InlineKeyboardButton("Book", callback_data=f"Book")],
            [InlineKeyboardButton("Cancel", callback_data="Done")]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text=f"{facility} is available. Do you want to book it?", 
            reply_markup=reply_markup
        )
    else:
        context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text=f"Sorry, {facility} is currently booked."
        )

def handle_instant_booking(update, context):
    query= update.callback_query
    
    start_time = context.chat_data['start_time']
    end_time = context.chat_data['end_time']

    start_time_str = start_time.strftime('%H:%M')
    end_time_str = end_time.strftime('%H:%M')
    
    context.chat_data['start_time'] = start_time_str
    context.chat_data['end_time'] = end_time_str
    response_text = f"{context.chat_data['selected_facility']} selected\nDate: {context.chat_data['today_date']}\nStart: {start_time_str} \nEnd: {end_time_str} \nConfirm booking?"
    
    keyboard = [[InlineKeyboardButton("Yes", callback_data='Accept Booking'),InlineKeyboardButton("No", callback_data='Abort Booking')],
    [InlineKeyboardButton("Back", callback_data='Instant Booking')]]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    print(start_time)
    context.bot.edit_message_text(chat_id=query.message.chat_id, 
    message_id=query.message.message_id, 
    text=response_text, 
    reply_markup=reply_markup)

def check_currently_booked(curr_date, curr_time, facility):
    with connect_to_sql() as conn:
        cursor=conn.cursor()
        query= ("SELECT * FROM Bookings " "WHERE facility_name = %s AND start_time <= %s AND end_time > %s AND date = %s AND cancelled = False")
        cursor.execute(query, (facility, curr_time, curr_time, curr_date))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        # if rows returned means the facility is booked
        return len(rows) > 0

### Check Booking Feature
def check_bookings(update, context):
    get_user_details(update, context)

    '''This function will show users which appointments they booked.'''
    username = context.chat_data['username']
    today_date = context.chat_data['today_date']
    booking_results = get_personal_bookings(username, today_date)
    keyboard = [[InlineKeyboardButton("Back", callback_data='Back')]]

    for booking_id, facility_name, date, start_time, end_time in booking_results:
        start_time = convert_to_12_hour_format(int(str(start_time).split(':')[0]))
        end_time = convert_to_12_hour_format(int(str(end_time).split(':')[0]))
        display_text = f"{facility_name} on {str(date)[5:]} from {start_time} to {end_time}"
        keyboard.append([InlineKeyboardButton(display_text ,callback_data = booking_id)])

    reply_markup = InlineKeyboardMarkup(keyboard)

    text="Select your Booking:"

    send_message(update, context, text, reply_markup)

def cancel_booking(update, context):
    '''This function will cancel the booking'''
    booking_id = context.chat_data['booking_id']

    with connect_to_sql() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE Bookings SET cancelled = TRUE WHERE booking_id = %s", (booking_id,))
        conn.commit()

    text = "Booking cancelled.\n\nTo make another booking, enter /quick_booking or /advance_booking"

    context.bot.edit_message_text(chat_id=update.effective_chat.id, 
        message_id=update.callback_query.message.message_id, 
        text=text)

def handle_selected_booking(update, context):
    '''This function will show what the user can do for their booking'''
    context.chat_data['booking_id'] = update.callback_query.data

    keyboard = [[InlineKeyboardButton("Cancel Booking", callback_data="Cancel Booking"), InlineKeyboardButton("Done", callback_data="Done")],
        [InlineKeyboardButton("Back", callback_data="Check Booking")]]

    booking_result = get_booking_details_with_id(update.callback_query.data)
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = f"""Facility: {booking_result[0]}\nDate: {booking_result[1]}\nStart Time: {booking_result[2]}\nEnd Time: {booking_result[3]}\n\nSelect an option:"""

    context.bot.edit_message_text(chat_id=update.effective_chat.id, 
        message_id=update.callback_query.message.message_id, 
        text=text,
        reply_markup=reply_markup)

def handle_cancel_booking(update, context):
    '''This function will ask user to confirm the cancellation request.'''
    booking_id = context.chat_data['booking_id']
    booking_result = get_booking_details_with_id(booking_id)

    keyboard = [[InlineKeyboardButton("Yes", callback_data="Confirm Cancel")],
        [InlineKeyboardButton("Back", callback_data=booking_id)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = f"Facility: {booking_result[0]}\nDate: {booking_result[1]}\nStart Time: {booking_result[2]}\nEnd Time: {booking_result[3]}\n\nAre you sure you want to cancel?"

    context.bot.edit_message_text(chat_id=update.effective_chat.id, 
        message_id=update.callback_query.message.message_id, 
        text=text,
        reply_markup=reply_markup)

def handle_done_booking(update, context):
    query = update.callback_query

    text = "Thank you for using ORCAChopes Have a nice day!"

    context.bot.edit_message_text(chat_id=query.message.chat_id, 
        message_id=query.message.message_id, 
        text=text)

def get_personal_bookings(username, date):
    '''This function will show users which appointments they booked.'''
    with connect_to_sql() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT booking_id, facility_name, date, start_time, end_time FROM Bookings WHERE username = %s AND cancelled!= TRUE  AND date >= %s", (username, date))
        booking_data = cursor.fetchall()
        return booking_data

def get_booking_details_with_id(booking_id):
    '''This function will return the booking details with the booking_id'''
    with connect_to_sql() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT facility_name, date, start_time, end_time FROM Bookings WHERE booking_id = %s", (booking_id,))
        booking_data = cursor.fetchone()
        return booking_data

### Advanced Booking Feature
def advanced_booking(update, context):
    '''This function will allow user to book up to 7 days in advance.'''
    get_user_details(update, context)

    keyboard = [[InlineKeyboardButton("Back", callback_data='Back')],
        [InlineKeyboardButton("Pool Table", callback_data='(Advance) Pool Table')],
        [InlineKeyboardButton("Mahjong Table", callback_data='(Advance) Mahjong Table')],
        [InlineKeyboardButton("Foosball", callback_data='(Advance) Foosball')],
        [InlineKeyboardButton("Darts", callback_data='(Advance) Darts')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "Advance Booking selected. \nYou may book up to 7 days in advance. \nPlease select your facility:"

    send_message(update, context, text, reply_markup)

def show_booking_dates(update, context):
    '''This function will allow user to choose dates to book'''
    response = update.callback_query.data
    facility = response.split(") ")[1]
    context.chat_data['selected_facility'] = facility

    available_dates = get_advance_booking_dates()
    keyboard = [[InlineKeyboardButton("Back", callback_data="Advance Booking")]]
    for date in available_dates:
        keyboard.append([InlineKeyboardButton(date, callback_data=f"Select Time, {date}")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "Please select your date:"

    context.bot.edit_message_text(chat_id=update.effective_chat.id, 
        message_id=update.callback_query.message.message_id, 
        text=text,
        reply_markup=reply_markup)

def get_user_timing(update, context):
    '''This function will register the user input time if it is valid'''
    user_input = update.message.text

    if user_input == "/cancel":
        update.message.reply_text("Thank for using ORCAChopes.")
        return ConversationHandler.END

    booked_slots = get_booked_slots(context.chat_data['selected_facility'],
            context.chat_data['selected_date'])
    try:
        validate_user_input(user_input)
        start_time, end_time = user_input.split('-')
        check_interval_overlap(start_time, end_time, booked_slots)
        start_time = datetime.strptime(start_time, '%H%M').time()
        end_time = datetime.strptime(end_time, '%H%M').time()

        context.chat_data['start_time'] = start_time
        context.chat_data['end_time'] = end_time

        text = f"{context.chat_data['selected_facility']} selected\nDate:{context.chat_data['selected_date']}\nStart Time: {start_time} \nEnd Time: {end_time} \nConfirm booking?"
        keyboard = [[InlineKeyboardButton("Yes", callback_data='Accept Booking'), InlineKeyboardButton("No", callback_data='Abort Booking')],
            [InlineKeyboardButton("Back", callback_data=f"Select Time, {context.chat_data['selected_date']}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        context.bot.send_message(chat_id=update.effective_chat.id, 
            text=text, 
            reply_markup=reply_markup)
        return ConversationHandler.END

    except Exception as e:
        update.message.reply_text(str(e))
        return ADVANCE_BOOKING

def get_available_timings(date, facility):
    available_timings = []
    start = timedelta(hours=10)#datetime.now().hour)
    end = timedelta(hours=22)
    booked_timings = get_booked_slots(facility, date)
    booked_timings.sort()
    print(booked_timings)
    while booked_timings:
        booked_slot = booked_timings[0]
        if start < booked_slot[0]:
            available_timings.append((start, booked_slot[0]))
        start = booked_slot[1]
        booked_timings = booked_timings[1:]
    if start < end:
        available_timings.append((start,end))
    available_timings = list(map(lambda x: f'{format_timedelta(x[0])} - {format_timedelta(x[1])}',available_timings))
    available_timings = '\n'.join(available_timings)
    return available_timings

### Report Feature
def report_issue(update, context): 
    '''Command Handler for Report Issue Feature'''
    get_user_details(update, context)

    keyboard = [[InlineKeyboardButton("Back", callback_data='Back')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "Please provide your comment for the issue\nTo cancel the report, type /cancel"

    send_message(update, context, text, reply_markup)
    return STATE_COMMENT
    
def handle_report_comment(update, context):
    '''This feature will help to insert the report into the database.'''
    user_input = update.message.text

    if user_input == "/report":
        raise Exception("Invalid!")
    elif user_input == "/cancel":
        terminate_input(update, context)
    else:
        with connect_to_sql() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO Reports (username, datetime, remarks) VALUES (%s, %s, %s)",
                (context.chat_data['username'] , datetime.now(), user_input))
            conn.commit()
            update.message.reply_text("Your feedback has been submitted. Thank You.")
        
    return ConversationHandler.END

def terminate_input(update, context):
    '''This function will stop collecting the user's input.'''
    update.message.reply_text("Thank for using ORCAChopes.")
    return ConversationHandler.END

if __name__ == '__main__':
    main()

def recurring_action(update, context):
    # Perform the desired action here
    with connect_to_sql as conn:
        cursor = conn.cursor()
        cursor.execute()
    context.bot.send_message(chat_id="YOUR_CHAT_ID", text="This is a recurring action!")
