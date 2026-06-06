import sqlite3
conn = sqlite3.connect('database.db')
cur = conn.cursor()
cur.execute("CREATE TABLE IF NOT EXISTS import_queue (id INTEGER PRIMARY KEY AUTOINCREMENT, filename TEXT, data BLOB, status TEXT, attempts INTEGER, error TEXT, created_at TEXT, processed_at TEXT)")
conn.commit()
conn.close()
print('import_queue table ensured')
