import sqlite3

def db_connection():
    try:
        conn = sqlite3.connect("university.db")
        print("Db connect")
        return conn
    except Exception as e:
        print(f"Db not connect: {e}")
        return
