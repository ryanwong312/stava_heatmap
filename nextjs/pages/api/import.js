import formidable from 'formidable';
import fs from 'fs';
import { XMLParser } from 'fast-xml-parser';
import path from 'path';
import db from '../../lib/db';

export const config = { api: { bodyParser: false } };

function haversineKm(a, b) {
  const toRad = (v) => v * Math.PI / 180;
  const lat1 = toRad(a[0]), lon1 = toRad(a[1]);
  const lat2 = toRad(b[0]), lon2 = toRad(b[1]);
  const dlat = lat2 - lat1, dlon = lon2 - lon1;
  const R = 6371.0;
  const hav = Math.sin(dlat/2)**2 + Math.cos(lat1)*Math.cos(lat2)*Math.sin(dlon/2)**2;
  return 2 * R * Math.asin(Math.sqrt(hav));
}

export default async function handler(req, res) {
  if (req.method !== 'POST') return res.status(405).end();
  const form = formidable({ multiples: false });
  form.parse(req, async (err, fields, files) => {
    if (err) return res.status(500).json({ error: err.message });
    const f = files?.file;
    if (!f) return res.status(400).json({ error: 'no file' });
    const buf = fs.readFileSync(f.filepath);
    const name = path.basename(f.originalFilename || f.newFilename || 'upload');
    const lower = name.toLowerCase();
    let coords = [];
    try {
      if (lower.endsWith('.gpx') || lower.endsWith('.gpx.gz')) {
        const xml = buf.toString('utf8');
        const parser = new XMLParser({ ignoreAttributes: false });
        const j = parser.parse(xml);
        const trk = j.gpx?.trk;
        if (trk) {
          const segs = Array.isArray(trk) ? trk.flatMap(t => t.trkseg || []) : (trk.trkseg ? (Array.isArray(trk.trkseg) ? trk.trkseg : [trk.trkseg]) : []);
          // simple extraction
          const pts = [];
          const collect = (seg) => {
            const trkpt = seg.trkpt || [];
            const arr = Array.isArray(trkpt) ? trkpt : [trkpt];
            arr.forEach(p => {
              const lat = parseFloat(p['@_lat']);
              const lon = parseFloat(p['@_lon']);
              if (!isNaN(lat) && !isNaN(lon)) pts.push([lat, lon]);
            });
          };
          segs.forEach(s => collect(s));
          coords = pts;
        }
      } else {
        return res.status(400).json({ error: 'only .gpx supported in this scaffold' });
      }
    } catch (e) {
      return res.status(500).json({ error: e.message });
    }

    let distance = 0;
    for (let i=1;i<coords.length;i++) distance += haversineKm(coords[i-1], coords[i]);
    const start_time = null;
    const duration_seconds = null;

    const info = db.prepare('INSERT INTO activities (name, filename, start_time, distance_km, duration_seconds, coords_json) VALUES (?, ?, ?, ?, ?, ?)').run(name, name, start_time, distance, duration_seconds, JSON.stringify(coords));
    res.json({ added: 1, id: info.lastInsertRowid });
  });
}
