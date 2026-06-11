# to run the server: 
# python app.py

from flask import Flask, request, render_template, url_for, redirect, jsonify, flash, session
from helpers import parse_gpx_bytes, insert_activity, get_activities
import sqlite3
from datetime import datetime
from filters import *
from forms import *
import secrets
import os

BASE_URL = "stava"
DEFAULT_GOOGLE_MAPS_API_KEY = os.environ.get('GOOGLE_MAPS_API_KEY', 'AIzaSyBQmrQmqsx8vYXLb42SJ8zFZ_0u5YNyjXs')


def reset_database():
    if os.path.exists('database.db'):
        os.remove('database.db')
    conn = sqlite3.connect('database.db')
    try:
        with open('db_definition.sql') as schema_file:
            conn.executescript(schema_file.read())
    finally:
        conn.close()


app = Flask(__name__)
app.secret_key = secrets.token_hex(32)


@app.route(f"/{BASE_URL}/")
def home():
    """Home page - landing page with navigation"""
    return render_template('home.html')


@app.route(f"/{BASE_URL}/map/")
def index():
    if not session.get('started'):
        reset_database()
        session['started'] = True
    return render_template(
        'index.html',
        GOOGLE_MAPS_API_KEY=DEFAULT_GOOGLE_MAPS_API_KEY,
    )


@app.route(f"/{BASE_URL}/stats/")
def stats():
    """Statistics page"""
    return render_template('stats.html')


@app.route(f"/{BASE_URL}/import", methods=['GET', 'POST'])
def import_files():
    # Keep GET render for manual browsing
    if request.method == 'GET':
        return render_template('import.html')

    # POSTs to this route are expected to be form uploads from the legacy form
    files = request.files.getlist('files')
    added = 0
    errors = []
    for f in files:
        filename = f.filename
        data = f.read()
        try:
            parsed = parse_gpx_bytes(data, filename=filename)
            name = os.path.splitext(filename)[0]
            insert_activity(name, filename, parsed)
            added += 1
        except Exception as e:
            errors.append(f"{filename}: {e}")

    flash(f'Imported {added} files')
    if errors:
        flash('Some files failed to import: ' + '; '.join(errors))

    return redirect(url_for('index'))


@app.route(f"/{BASE_URL}/api/import", methods=['POST'])
def api_import():
    # JSON API for AJAX uploads; returns JSON with inserted count and errors
    files = request.files.getlist('files')
    added = 0
    errors = []
    for f in files:
        filename = f.filename
        data = f.read()
        try:
            parsed = parse_gpx_bytes(data, filename=filename)
            name = os.path.splitext(filename)[0]
            insert_activity(name, filename, parsed)
            added += 1
        except Exception as e:
            errors.append(f"{filename}: {e}")

    return jsonify({'added': added, 'errors': errors})


@app.route(f"/{BASE_URL}/api/queue_import", methods=['POST'])
def api_queue_import():
    # enqueue uploaded files for background processing
    files = request.files.getlist('files')
    queued = 0
    errors = []
    conn = None
    try:
        conn = sqlite3.connect('database.db')
        cur = conn.cursor()
        for f in files:
            name = f.filename
            data = f.read()
            try:
                cur.execute('INSERT INTO import_queue (filename, data, status, attempts, created_at) VALUES (?, ?, ?, ?, ?)',
                            (name, data, 'queued', 0, datetime.utcnow().isoformat()))
                queued += 1
            except Exception as e:
                errors.append(f"{name}: {e}")
        conn.commit()
    finally:
        if conn: conn.close()
    return jsonify({'queued': queued, 'errors': errors})


@app.route(f"/{BASE_URL}/api/process_queue", methods=['POST'])
def api_process_queue():
    # process up to 'limit' queued items synchronously
    limit = int(request.args.get('limit', 10))
    processed = 0
    failed = []
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS import_queue (id INTEGER PRIMARY KEY AUTOINCREMENT, filename TEXT, data BLOB, status TEXT, attempts INTEGER, error TEXT, created_at TEXT, processed_at TEXT)")
    rows = cur.execute("SELECT id, filename, data, attempts FROM import_queue WHERE status = 'queued' ORDER BY id LIMIT ?", (limit,)).fetchall()
    for row in rows:
        qid, filename, data_blob, attempts = row
        try:
            parsed = parse_gpx_bytes(data_blob, filename=filename)
            name = os.path.splitext(filename)[0]
            insert_activity(name, filename, parsed)
            cur.execute("UPDATE import_queue SET status='done', processed_at=? WHERE id=?", (datetime.utcnow().isoformat(), qid))
            processed += 1
        except Exception as e:
            attempts = (attempts or 0) + 1
            cur.execute("UPDATE import_queue SET attempts=?, status='error', error=? WHERE id=?", (attempts, str(e), qid))
            failed.append({ 'id': qid, 'filename': filename, 'error': str(e) })
    conn.commit()
    conn.close()
    return jsonify({'processed': processed, 'failed': failed})


@app.route(f"/{BASE_URL}/api/debug")
def api_debug():
    # return quick summary of activities and a sample
    try:
        acts = get_activities(0)
        sample = None
        if acts:
            a = acts[0]
            sample = {
                'id': a['id'], 'name': a['name'], 'distance_km': a['distance_km'],
                'coords_count': len(a.get('coords') or []),
                'first_coord': a.get('coords')[0] if a.get('coords') else None,
            }
        return jsonify({'count': len(acts), 'sample': sample})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route(f"/{BASE_URL}/api/activities")
def api_activities():
    min_km = float(request.args.get('min_km', 0) or 0)
    activities = get_activities(min_km)
    return jsonify(activities)


@app.route(f"/{BASE_URL}/api/stats-summary")
def api_stats_summary():
    """Get statistics summary for the stats page"""
    try:
        acts = get_activities(0)
        if not acts:
            return jsonify({
                'total_activities': 0,
                'total_distance': 0,
                'total_time': 0,
                'avg_distance': 0,
                'avg_pace': 'N/A',
                'monthly_data': {},
                'all_activities': []
            })
        
        total_distance = sum(a['distance_km'] for a in acts)
        total_time = sum(a['duration_seconds'] or 0 for a in acts)
        avg_distance = total_distance / len(acts) if acts else 0
        
        # Calculate average pace
        avg_pace = 'N/A'
        if total_distance > 0 and total_time > 0:
            pace_seconds = total_time / total_distance
            pace_mins = int(pace_seconds // 60)
            pace_secs = int(pace_seconds % 60)
            avg_pace = f"{pace_mins}:{str(pace_secs).zfill(2)} min/km"
        
        # Group by month
        monthly_data = {}
        for act in acts:
            if act['start_time']:
                try:
                    date = datetime.fromisoformat(act['start_time'])
                    month_key = date.strftime('%Y-%m')
                    if month_key not in monthly_data:
                        monthly_data[month_key] = {'count': 0, 'distance': 0, 'time': 0}
                    monthly_data[month_key]['count'] += 1
                    monthly_data[month_key]['distance'] += act['distance_km']
                    monthly_data[month_key]['time'] += act['duration_seconds'] or 0
                except:
                    pass
        
        return jsonify({
            'total_activities': len(acts),
            'total_distance': round(total_distance, 2),
            'total_time': total_time,
            'avg_distance': round(avg_distance, 2),
            'avg_pace': avg_pace,
            'monthly_data': monthly_data,
            'all_activities': acts
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route(f"/{BASE_URL}/api/reset", methods=['POST'])
def api_reset():
    """Reset the entire database"""
    try:
        reset_database()
        return jsonify({'success': True, 'message': 'Database reset successfully'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route(f"/{BASE_URL}/api/delete/<int:activity_id>", methods=['DELETE'])
def api_delete_activity(activity_id):
    """Delete a specific activity by ID"""
    try:
        conn = sqlite3.connect('database.db')
        cur = conn.cursor()
        cur.execute("DELETE FROM activities WHERE id = ?", (activity_id,))
        conn.commit()
        if cur.rowcount == 0:
            conn.close()
            return jsonify({'success': False, 'error': 'Activity not found'}), 404
        conn.close()
        return jsonify({'success': True, 'message': 'Activity deleted successfully'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
