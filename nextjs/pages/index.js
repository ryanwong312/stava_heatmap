import { useEffect } from 'react';

export default function Home() {
  useEffect(() => {
    const init = async () => {
      const res = await fetch('/api/activities');
      const data = await res.json();
      // simple client-side leaflet setup
      const LScript = document.createElement('script');
      LScript.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';
      LScript.onload = () => {
        const link = document.createElement('link');
        link.rel = 'stylesheet';
        link.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';
        document.head.appendChild(link);
        const mapDiv = document.getElementById('map');
        const map = window.L.map(mapDiv).setView([0,0],2);
        window.L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);
        data.forEach(act => {
          if(!act.coords || !act.coords.length) return;
          window.L.polyline(act.coords.map(c=>[c[0],c[1]])).addTo(map);
        });
      };
      document.body.appendChild(LScript);
    };
    init();
  }, []);

  return (
    <div style={{padding:20}}>
      <h1>Run Map (Next.js)</h1>
      <div id="map" style={{height:600}}></div>
    </div>
  );
}
