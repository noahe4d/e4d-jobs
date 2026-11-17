/**
 * E4D checklist: shared store for "Built" and "Taken to site" ticks.
 * Paste into a Google Sheet's Extensions > Apps Script, then Deploy > New deployment >
 * Web app, Execute as: Me, Who has access: Anyone. Put the /exec URL in checklist-config.js.
 * Every tick is one row on the "Ticks" tab, so the office can see who ticked what and when.
 */
const TAB = 'Ticks';
const HEAD = ['Time', 'Job', 'List', 'Part key', 'Ticked', 'Who', 'Id'];

function tab_() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sh = ss.getSheetByName(TAB);
  if (!sh) {
    sh = ss.insertSheet(TAB);
    sh.appendRow(HEAD);
    sh.setFrozenRows(1);
  }
  return sh;
}

function out_(o) {
  return ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON);
}

// GET ?job=<job-folder>  ->  {ok, rows:[[timeMs, list, key, on, who], ...]}
function doGet(e) {
  try {
    const job = String((e.parameter || {}).job || '');
    if (!job) return out_({ok: false, error: 'no job'});
    const sh = tab_(), n = sh.getLastRow();
    const rows = [];
    if (n > 1) {
      sh.getRange(2, 1, n - 1, 6).getValues().forEach(r => {
        if (r[1] === job) rows.push([new Date(r[0]).getTime(), r[2], r[3], r[4] === true || r[4] === 'TRUE', r[5]]);
      });
    }
    return out_({ok: true, rows: rows});
  } catch (err) {
    return out_({ok: false, error: String(err)});
  }
}

// POST {job, ev:[{id, t, list, key, on, who}]}  ->  {ok}
function doPost(e) {
  const lock = LockService.getScriptLock();
  try {
    lock.waitLock(20000);
    const body = JSON.parse(e.postData.contents);
    const job = String(body.job || '');
    const ev = (body.ev || []).filter(x => x && x.key && (x.list === 'built' || x.list === 'site'));
    if (!job || !ev.length) return out_({ok: true, n: 0});
    const sh = tab_(), n = sh.getLastRow();
    // skip ticks already saved (a phone can resend if the reply was lost)
    const seen = new Set(n > 1 ? sh.getRange(Math.max(2, n - 3000), 7, Math.min(n - 1, 3000), 1).getValues().map(r => r[0]) : []);
    const rows = ev.filter(x => !seen.has(x.id)).map(x =>
      [new Date(Number(x.t) || Date.now()), job, x.list, String(x.key), !!x.on, String(x.who || '').slice(0, 60), String(x.id)]);
    if (rows.length) sh.getRange(n + 1, 1, rows.length, HEAD.length).setValues(rows);
    return out_({ok: true, n: rows.length});
  } catch (err) {
    return out_({ok: false, error: String(err)});
  } finally {
    lock.releaseLock();
  }
}
