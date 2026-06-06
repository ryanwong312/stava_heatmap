export default function ImportPage(){
  async function handle(e){
    e.preventDefault();
    const f = document.getElementById('file').files[0];
    if(!f) return alert('select a file');
    const fd = new FormData(); fd.append('file', f);
    const res = await fetch('/api/import', { method: 'POST', body: fd });
    const j = await res.json();
    alert(JSON.stringify(j));
  }
  return (<div style={{padding:20}}>
    <h1>Import</h1>
    <form onSubmit={handle}>
      <input id="file" type="file" accept=".gpx" />
      <button>Upload</button>
    </form>
  </div>)
}
