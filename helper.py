from datetime import time, datetime, timedelta

### Helper Functions
def convert_to_12_hour_format(hour):
    '''This function will help to convert an integer to 12H time string'''
    if hour < 0 or hour > 23:
        raise ValueError("Invalid hour: must be between 0 and 23")

    if hour == 0:
        formatted_hour = 12
        suffix = "AM"
    elif hour < 12:
        formatted_hour = hour
        suffix = "AM"
    elif hour == 12:
        formatted_hour = 12
        suffix = "PM"
    else:
        formatted_hour = hour - 12
        suffix = "PM"

    formatted_time = f"{formatted_hour:02d}:00 {suffix}"

    return formatted_time

def get_session_info(session):
    hour = int(session[8:]) + 6
    return (time(hour=hour), time(hour=hour+1))

def get_advance_booking_dates():
    '''This function will get dates available for advance booking'''
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

def check_interval_overlap(start_time, end_time, intervals):
    start = datetime.strptime(start_time, "%H%M")
    end = datetime.strptime(end_time, "%H%M")
    start = start.hour * 60 * 60 + start.minute * 60
    end = end.hour * 60 * 60 + end.minute * 60

    for interval in intervals:
        interval_start = interval[0].total_seconds()
        interval_end = interval[1].total_seconds()
        if (start >= interval_start and start < interval_end) or (end > interval_start and end > interval_end):
            raise Exception("The timing selected has already been booked. Please enter another timing.")
    return True

def validate_user_input(user_input):
    '''This function will make sure user enter their input according to the stated format'''
    try:
        start_time, end_time = user_input.split('-')
        start_time = datetime.strptime(start_time, '%H%M')
        end_time = datetime.strptime(end_time, '%H%M')
        if (start_time >= end_time) or (start_time.minute % 30 != 0 or end_time.minute % 30 != 0):
            raise Exception("Invalid Input! \nPlease check your input and enter again: \n\nTo terminate booking, type /end")
        else:
            return True
    except Exception as e:
        raise Exception("Invalid Input! \nPlease check your input and enter again: \n\nTo terminate booking, type /end")

def format_timedelta(tdelta):
    hours = tdelta // timedelta(hours=1)
    minutes = (tdelta % timedelta(hours=1)) // timedelta(minutes=1)
    return f"{hours:02d}:{minutes:02d}"
