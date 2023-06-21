import mysql.connector

TOKEN = '6183521726:AAGqHZywmdqCp6JsoJnbi-AGbS4nRe31xyI'

def connect_to_sql():
    '''Establish connection to SQL database'''
    return mysql.connector.connect(
            host="localhost", 
            user="root",
            password="Password1!",
            database="ORCAChopes" 
            )