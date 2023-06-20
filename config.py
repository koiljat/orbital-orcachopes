import mysql.connector

TOKEN = '6183521726:AAGqHZywmdqCp6JsoJnbi-AGbS4nRe31xyI'

def connect_to_sql():
    '''Establish connection to SQL database'''
    return mysql.connector.connect(
            host="127.0.0.1", 
            user="root",
            password="Nerfcs45&",
            database="ORCAChopes" 
            )