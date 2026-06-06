import db from '../../lib/db';

export default function handler(req, res) {
  if (req.method !== 'GET') return res.status(405).end();
  const min_km = parseFloat(req.query.min_km || '0') || 0;
  const rows = db.prepare('SELECT * FROM activities WHERE distance_km >= ? ORDER BY start_time DESC').all(min_km);
  const activities = rows.map(r => ({
    id: r.id,
    name: r.name,
    filename: r.filename,
    start_time: r.start_time,
    distance_km: r.distance_km,
    duration_seconds: r.duration_seconds,
    coords: r.coords_json ? JSON.parse(r.coords_json) : []
  }));
  res.json(activities);
}
