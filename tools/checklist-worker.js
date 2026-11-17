// E4D checklist store (Cloudflare Worker + D1). One row per tick.
// GET  ?job=<job-folder>          -> {ok, rows:[[timeMs, list, key, on, who], ...]}
// POST {job, ev:[{id,t,list,key,on,who}]} -> {ok, n}
const H = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
  'Content-Type': 'application/json',
  'Cache-Control': 'no-store'
};
const out = (o, s = 200) => new Response(JSON.stringify(o), {status: s, headers: H});

let ready = false;
async function setup(db) {
  if (ready) return;
  await db.batch([
    db.prepare('CREATE TABLE IF NOT EXISTS ticks (id TEXT PRIMARY KEY, t INTEGER NOT NULL, job TEXT NOT NULL, list TEXT NOT NULL, k TEXT NOT NULL, onv INTEGER NOT NULL, who TEXT)'),
    db.prepare('CREATE INDEX IF NOT EXISTS ticks_job ON ticks(job, t)')
  ]);
  ready = true;
}

export default {
  async fetch(req, env) {
    if (req.method === 'OPTIONS') return new Response(null, {headers: H});
    try {
      await setup(env.DB);
      const url = new URL(req.url);
      if (req.method === 'GET') {
        const job = url.searchParams.get('job');
        if (!job) return out({ok: true, service: 'e4d-checklist'});
        const {results} = await env.DB.prepare('SELECT t, list, k, onv, who FROM ticks WHERE job = ? ORDER BY t').bind(job).all();
        return out({ok: true, rows: results.map(r => [r.t, r.list, r.k, !!r.onv, r.who])});
      }
      if (req.method === 'POST') {
        const body = JSON.parse(await req.text());
        const job = String(body.job || '').slice(0, 100);
        const ev = (body.ev || []).filter(x => x && x.id && x.key && (x.list === 'built' || x.list === 'site')).slice(0, 2000);
        if (!job || !ev.length) return out({ok: true, n: 0});
        const st = env.DB.prepare('INSERT OR IGNORE INTO ticks (id, t, job, list, k, onv, who) VALUES (?, ?, ?, ?, ?, ?, ?)');
        const res = await env.DB.batch(ev.map(x => st.bind(String(x.id).slice(0, 80), Number(x.t) || Date.now(), job, x.list,
          String(x.key).slice(0, 60), x.on ? 1 : 0, String(x.who || '').slice(0, 60))));
        return out({ok: true, n: res.reduce((a, r) => a + (r.meta.changes || 0), 0)});
      }
      return out({ok: false, error: 'method'}, 405);
    } catch (e) {
      return out({ok: false, error: String(e)}, 500);
    }
  }
};
