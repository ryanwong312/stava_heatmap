import sqlite3, json
conn = sqlite3.connect('database.db')
cur = conn.cursor()
rows = cur.execute('SELECT id,name,filename,start_time,distance_km,duration_seconds,coords_json FROM activities ORDER BY id DESC').fetchall()
print('rows:', len(rows))
for r in rows[:10]:
    id,name,fn,start,dist,dur,coords_json = r
    coords = []
    try:
        coords = json.loads(coords_json) if coords_json else []
    except Exception as e:
        coords = str(coords_json)[:120]
    print(id, name, fn, '|', dist, 'km', '| coords:', len(coords))
conn.close()
