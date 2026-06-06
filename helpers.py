import sqlite3
import json
import gpxpy
import gzip
import io
import math
from datetime import datetime

try:
    from fitparse import FitFile
except Exception:
    FitFile = None


def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn


def haversine_km(a, b):
    lat1, lon1 = math.radians(a[0]), math.radians(a[1])
    lat2, lon2 = math.radians(b[0]), math.radians(b[1])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    R = 6371.0
    hav = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    return 2 * R * math.asin(math.sqrt(hav))


def parse_gpx_bytes(data_bytes, filename=None):
    """Parse GPX or FIT data from bytes. Returns dict with coords, distance_km, start_time, duration_seconds."""
    lower = (filename or '').lower()
    is_fit = lower.endswith('.fit') or lower.endswith('.fit.gz') or lower.endswith('.fit.zip')

    # If the filename indicates FIT, try FIT parsing first
    if is_fit:
        if FitFile is None:
            raise RuntimeError("fitparse not installed; run 'pip install fitparse' to import .fit files")
        try:
            raw = data_bytes
            try:
                raw = gzip.decompress(data_bytes)
            except Exception:
                pass
            fb = io.BytesIO(raw)
            ffile = FitFile(fb)
            coords = []
            times = []
            for record in ffile.get_messages('record'):
                lat = record.get_value('position_lat')
                lon = record.get_value('position_long')
                t = record.get_value('timestamp')
                if lat is not None and lon is not None:
                    # fit semicircles to degrees; include timestamp if available
                    coords.append([lat * (180.0 / 2**31), lon * (180.0 / 2**31), t.isoformat() if t is not None else None])
                if t is not None:
                    times.append(t)

            distance = 0.0
            for i in range(1, len(coords)):
                distance += haversine_km(coords[i-1], coords[i])

            start_time = times[0].isoformat() if times else None
            duration_seconds = int((times[-1] - times[0]).total_seconds()) if len(times) >= 2 else None

            return {
                'coords': coords,
                'distance_km': distance,
                'start_time': start_time,
                'duration_seconds': duration_seconds,
            }
        except Exception as e:
            raise RuntimeError(f"Failed parsing FIT file: {e}")

    # otherwise try GPX: plain text then gzipped
    gpx = None
    try:
        text = data_bytes.decode('utf-8')
        gpx = gpxpy.parse(text)
    except Exception:
        try:
            text = gzip.decompress(data_bytes).decode('utf-8')
            gpx = gpxpy.parse(text)
        except Exception:
            # as last resort, if fitparse available try FIT parsing
            if FitFile is not None:
                try:
                    raw = data_bytes
                    try:
                        raw = gzip.decompress(data_bytes)
                    except Exception:
                        pass
                    fb = io.BytesIO(raw)
                    ffile = FitFile(fb)
                    coords = []
                    times = []
                    for record in ffile.get_messages('record'):
                        lat = record.get_value('position_lat')
                        lon = record.get_value('position_long')
                        t = record.get_value('timestamp')
                        if lat is not None and lon is not None:
                            coords.append([lat * (180.0 / 2**31), lon * (180.0 / 2**31)])
                        if t is not None:
                            times.append(t)
                    distance = 0.0
                    for i in range(1, len(coords)):
                        distance += haversine_km(coords[i-1], coords[i])
                    start_time = times[0].isoformat() if times else None
                    duration_seconds = int((times[-1] - times[0]).total_seconds()) if len(times) >= 2 else None
                    return {
                        'coords': coords,
                        'distance_km': distance,
                        'start_time': start_time,
                        'duration_seconds': duration_seconds,
                    }
                except Exception as e:
                    raise RuntimeError(f"Failed parsing file as GPX or FIT: {e}")
            raise RuntimeError("Failed parsing file as GPX (not valid UTF-8 nor gzipped GPX)")

    # Extract coords and times from parsed GPX
    coords = []
    times = []
    for track in gpx.tracks:
        for segment in track.segments:
            for point in segment.points:
                coords.append([point.latitude, point.longitude, point.time.isoformat() if point.time else None])
                if point.time:
                    times.append(point.time)

    distance = 0.0
    for i in range(1, len(coords)):
        distance += haversine_km(coords[i-1], coords[i])

    start_time = times[0].isoformat() if times else None
    duration_seconds = int((times[-1] - times[0]).total_seconds()) if len(times) >= 2 else None

    return {
        'coords': coords,
        'distance_km': distance,
        'start_time': start_time,
        'duration_seconds': duration_seconds,
    }


def insert_activity(name, filename, parsed, activity_type='run'):
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Format name from start_time if available, otherwise use provided name
    start_time_str = parsed.get('start_time')
    if start_time_str:
        try:
            dt = datetime.fromisoformat(start_time_str)
            display_name = dt.strftime('%b %d, %Y')  # e.g., "Jan 15, 2024"
        except Exception:
            display_name = name or filename or 'Activity'
    else:
        display_name = name or filename or 'Activity'
    
    cur.execute(
        "INSERT INTO activities (name, filename, start_time, distance_km, duration_seconds, coords_json, activity_type) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (display_name, filename, parsed.get('start_time'), parsed.get('distance_km'), parsed.get('duration_seconds'), json.dumps(parsed.get('coords')), activity_type)
    )
    conn.commit()
    last = cur.execute("SELECT * FROM activities WHERE id = ?", (cur.lastrowid,)).fetchone()
    conn.close()
    return last


def get_activities(min_distance_km=0.0):
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM activities WHERE distance_km >= ? ORDER BY start_time desc", (min_distance_km,)).fetchall()
    activities = []
    for r in rows:
        activities.append({
            'id': r['id'],
            'name': r['name'],
            'filename': r['filename'],
            'start_time': r['start_time'],
            'distance_km': r['distance_km'],
            'duration_seconds': r['duration_seconds'],
            'coords': json.loads(r['coords_json']) if r['coords_json'] else [],
            'activity_type': r['activity_type'] if 'activity_type' in r.keys() else 'run'
        })
    conn.close()
    return activities


if __name__ == '__main__':
    print('helpers module run directly')
