# init_db.py
# ------
# run this Python file to create the database.db file
# open database.db in DB Browser to view database
# (to reset the database, delete the database.db file, re-run this file)
# ----------------------


import sqlite3

connection = sqlite3.connect('database.db')

# open db_definition.sql and execute it to create tables
with open('db_definition.sql') as file:
    connection.executescript(file.read())

connection.close()

print("-- database initialized --")