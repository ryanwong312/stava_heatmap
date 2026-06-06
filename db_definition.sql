-- Use this file to define your SQL table structure
-- 1) Replace TABLE_NAME 
-- 2) Add appropriate fields with the data type


-- activities table to store parsed runs
CREATE TABLE IF NOT EXISTS activities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    filename TEXT,
    start_time TEXT,
    distance_km REAL,
    duration_seconds INTEGER,
    coords_json TEXT,
    activity_type TEXT DEFAULT 'run'
);


