const Database = require('better-sqlite3');
const path = require('path');
const dbPath = path.resolve(process.cwd(), 'next_data.sqlite');
const db = new Database(dbPath);

db.exec(`
CREATE TABLE IF NOT EXISTS activities (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT,
  filename TEXT,
  start_time TEXT,
  distance_km REAL,
  duration_seconds INTEGER,
  coords_json TEXT
);
`);

module.exports = db;
