"""
LinkedIn Job Scanner — Public Web App
Built with Claude Code | Dreamshot AI Studio
"""

import uuid
import base64
import io
import threading
from datetime import datetime
from flask import Flask, render_template_string, request, jsonify
from scanner import run_scan


def extract_text_from_file(b64: str, filename: str) -> str:
    """Extract plain text from a base64-encoded PDF or Word file."""
    try:
        data = base64.b64decode(b64)
        name = filename.lower()
        if name.endswith(".pdf"):
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(data))
            return " ".join(page.extract_text() or "" for page in reader.pages)
        elif name.endswith((".docx", ".doc")):
            from docx import Document
            doc = Document(io.BytesIO(data))
            return " ".join(p.text for p in doc.paragraphs)
    except Exception:
        pass
    return ""

app = Flask(__name__)

# In-memory scan store
scans: dict = {}

# ─── HTML Templates ──────────────────────────────────────────────

LANDING = """<!DOCTYPE html>
<html dir="rtl" lang="he">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>סורק משרות LinkedIn | Dreamshot AI</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Segoe UI',Arial,sans-serif;background:#0a0d14;color:#dde1ea;
     min-height:100vh;display:flex;flex-direction:column;align-items:center;
     justify-content:center;padding:24px;direction:rtl}
.card{background:#111827;border:1px solid #1e3a8a;border-radius:20px;
      padding:40px 48px;max-width:560px;width:100%;text-align:center}
.logo{font-size:13px;color:#475569;margin-bottom:24px;letter-spacing:1px;
      text-transform:uppercase}
h1{font-size:28px;color:#fff;margin-bottom:10px;line-height:1.3}
.sub{color:#64748b;font-size:14px;margin-bottom:32px;line-height:1.6}
.form{display:flex;flex-direction:column;gap:14px;text-align:right}
label{font-size:12px;color:#94a3b8;font-weight:600;margin-bottom:4px;
      display:block;text-align:right}
input,select{width:100%;padding:12px 16px;border-radius:10px;border:1px solid #1e3a8a;
             background:#0f172a;color:#e2e8f0;font-size:14px;outline:none;
             transition:border .2s}
input:focus,select:focus,textarea:focus{border-color:#3b82f6}
textarea{resize:vertical;font-family:inherit;font-size:13px}
::placeholder{color:#334155}
button{background:linear-gradient(135deg,#1d4ed8,#1e40af);color:#fff;border:none;
       padding:14px;border-radius:10px;font-size:15px;font-weight:700;cursor:pointer;
       transition:opacity .2s;margin-top:6px}
button:hover{opacity:.85}
button:disabled{opacity:.4;cursor:not-allowed}
.hint{font-size:11px;color:#334155;margin-top:20px}
.brand{display:flex;align-items:center;justify-content:center;gap:10px;
       margin-top:20px;padding-top:16px;border-top:1px solid #1e293b}
.brand-avatar{width:36px;height:36px;border-radius:50%;background:linear-gradient(135deg,#1d4ed8,#7c3aed);
              display:flex;align-items:center;justify-content:center;font-size:16px;flex-shrink:0}
.brand-text{text-align:right}
.brand-name{font-size:13px;font-weight:700;color:#e2e8f0}
.brand-sub{font-size:11px;color:#475569;margin-top:1px}
.brand-link{font-size:11px;color:#818cf8;text-decoration:none}
.brand-link:hover{text-decoration:underline}
.upload-zone{border:2px dashed #1e3a8a;border-radius:10px;padding:20px 16px;
             cursor:pointer;transition:border-color .2s;text-align:center;
             background:#0a0e1a;position:relative}
.upload-zone:hover,.upload-zone.over{border-color:#3b82f6;background:#0d1526}
.upload-zone input[type=file]{position:absolute;inset:0;opacity:0;cursor:pointer;width:100%;height:100%}
.upload-icon{font-size:28px;margin-bottom:6px}
.upload-main{font-size:13px;color:#94a3b8}
.upload-sub{font-size:11px;color:#475569;margin-top:4px}
.file-chosen{font-size:12px;color:#4ade80;margin-top:6px;display:none}
.or-paste{font-size:11px;color:#334155;text-align:center;margin:4px 0;cursor:pointer;
          text-decoration:underline;text-underline-offset:2px}
textarea{width:100%;padding:12px 16px;border-radius:10px;border:1px solid #1e3a8a;
         background:#0f172a;color:#e2e8f0;font-size:13px;outline:none;
         transition:border .2s;resize:vertical;font-family:inherit;display:none}
textarea:focus{border-color:#3b82f6}
</style>
</head>
<body>
<div class="card">
  <div class="logo">Dreamshot AI Studio</div>
  <h1>🔍 סורק משרות LinkedIn</h1>
  <p class="sub">הכנס תפקיד ומיקום — הסורק יחפש, ינקד וייצג את התוצאות בדוח מפורט</p>
  <form class="form" onsubmit="startScan(event)">
    <div>
      <label>תפקיד מבוקש</label>
      <input id="job" type="text" placeholder='למשל: Business Applications Manager' required>
    </div>
    <div>
      <label>מיקום</label>
      <input id="loc" type="text" value="Israel" placeholder="Israel / Tel Aviv / Remote">
    </div>
    <div>
      <label>רזומה (אופציונלי — משפר את דיוק הניקוד)</label>
      <div class="upload-zone" id="dropzone">
        <input type="file" id="resume_file" accept=".pdf,.doc,.docx"
               onchange="fileChosen(this)">
        <div class="upload-icon">📄</div>
        <div class="upload-main">גרור לכאן או לחץ לבחירת קובץ</div>
        <div class="upload-sub">PDF · Word (.docx / .doc)</div>
        <div class="file-chosen" id="file_chosen">✓ <span id="file_name"></span></div>
      </div>
      <div class="or-paste" onclick="togglePaste()">או הדבק טקסט ידנית ▾</div>
      <textarea id="resume_text" rows="4" placeholder="הדבק כאן טקסט חופשי מהרזומה..."></textarea>
    </div>
    <button id="btn" type="submit">הרץ סריקה</button>
  </form>
  <p class="hint">הסריקה לוקחת כ-5-8 דקות. נשאר בדף.</p>
  <div class="brand">
    <div class="brand-avatar">🎬</div>
    <div class="brand-text">
      <div class="brand-name">נבנה על ידי Moshe Schwartz</div>
      <div class="brand-sub">Dreamshot AI Studio &nbsp;·&nbsp; נבנה עם Claude Code</div>
      <a class="brand-link" href="https://www.instagram.com/dreamshot.ai.studio/" target="_blank">@dreamshot.ai.studio ↗</a>
    </div>
  </div>
</div>
<script>
function fileChosen(input) {
  const f = input.files[0];
  if (!f) return;
  document.getElementById('file_name').textContent = f.name;
  document.getElementById('file_chosen').style.display = 'block';
  document.getElementById('resume_text').style.display = 'none';
}

function togglePaste() {
  const ta = document.getElementById('resume_text');
  ta.style.display = ta.style.display === 'none' ? 'block' : 'none';
}

// drag-over highlight
const dz = document.getElementById('dropzone');
dz.addEventListener('dragover', e => { e.preventDefault(); dz.classList.add('over'); });
dz.addEventListener('dragleave', () => dz.classList.remove('over'));
dz.addEventListener('drop', e => { e.preventDefault(); dz.classList.remove('over'); });

function startScan(e) {
  e.preventDefault();
  const job  = document.getElementById('job').value.trim();
  const loc  = document.getElementById('loc').value.trim() || 'Israel';
  const text = document.getElementById('resume_text').value.trim();
  const file = document.getElementById('resume_file').files[0];
  document.getElementById('btn').disabled = true;
  document.getElementById('btn').textContent = '⏳ מתחיל...';

  function send(b64, name) {
    fetch('/start', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({job, loc, resume_text: text, resume_b64: b64, resume_name: name})
    })
    .then(r => r.json())
    .then(d => { window.location.href = '/scan/' + d.scan_id; });
  }

  if (file) {
    const reader = new FileReader();
    reader.onload = ev => send(ev.target.result.split(',')[1], file.name);
    reader.readAsDataURL(file);
  } else {
    send('', '');
  }
}
</script>
</body>
</html>"""


def build_report_html(jobs: list, job_title: str, location: str, elapsed: str, has_resume: bool = False) -> str:
    now        = datetime.now().strftime("%d/%m/%Y %H:%M")
    high_match = [j for j in jobs if j["score"] >= 70]

    def app_badge(n, raw):
        if n == -1: return '<span class="kpi kpi-gray">—</span>'
        if n <= 25:  return f'<span class="kpi kpi-green">🟢 {raw or str(n)}</span>'
        if n <= 100: return f'<span class="kpi kpi-orange">🟡 {n}+</span>'
        return f'<span class="kpi kpi-red">🔴 {n}+</span>'

    def days_badge(d):
        if d < 0: return '<span class="kpi kpi-gray">—</span>'
        if d <= 3:  return f'<span class="kpi kpi-green">⚡ פורסם לפני {d} ימים</span>'
        if d <= 14: return f'<span class="kpi kpi-orange">פורסם לפני {d} ימים</span>'
        return f'<span class="kpi kpi-red">פורסם לפני {d} ימים</span>'

    rows = ""
    for j in jobs:
        s   = j["score"]
        uid = f"j{j['job_id']}"
        if s >= 70:   badge = f'<span class="badge badge-high">גבוהה {s}%</span>'
        elif s >= 45: badge = f'<span class="badge badge-mid">בינונית {s}%</span>'
        else:         badge = f'<span class="badge badge-low">נמוכה {s}%</span>'

        comp_url  = j.get("company_url", "")
        comp_link = (f'<a href="{comp_url}" target="_blank" class="comp-link">{j["company"]}</a>'
                     if comp_url else j["company"])
        ea    = '<span class="kpi kpi-purple">Easy Apply</span>' if j.get("easy_apply") else ""
        ab    = app_badge(j.get("applicants_n", -1), j.get("applicants_raw",""))
        db    = days_badge(j.get("days_posted", -1))
        sen   = f'<span class="kpi kpi-gray">{j["seniority"]}</span>'   if j.get("seniority")   else ""
        emp   = f'<span class="kpi kpi-gray">{j["employment_type"]}</span>' if j.get("employment_type") else ""
        ind   = f'<span class="kpi kpi-gray">{j["industries"][:22]}</span>'  if j.get("industries")    else ""

        rows += f"""
        <tr onclick="toggle('{uid}')" style="cursor:pointer">
          <td>
            <a href="{j['job_url']}" target="_blank" class="jtitle"
               onclick="event.stopPropagation()">{j['title']}</a>
          </td>
          <td class="company">{comp_link}</td>
          <td>{j['location']}</td>
          <td>{badge}</td>
          <td class="kc">{ab} {db} {ea}</td>
          <td class="kc">{sen} {emp} {ind}</td>
        </tr>
        <tr id="{uid}" class="drow" style="display:none">
          <td colspan="6">
            <div class="dgrid">
              <div class="dbox">
                <div class="dlabel">📋 תיאור המשרה</div>
                <p class="dtext">{j.get('desc_summary','—')}</p>
                <a href="{j['job_url']}" target="_blank" class="more">קרא עוד בלינקדאין →</a>
              </div>
              <div class="dbox">
                <div class="dlabel">🏢 על החברה</div>
                <p class="dtext">{j.get('company_about','—') or '—'}</p>
                {'<a href="'+comp_url+'" target="_blank" class="more">עמוד החברה →</a>' if comp_url else ''}
              </div>
            </div>
          </td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html dir="rtl" lang="he">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>דוח משרות — {job_title}</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Segoe UI',Arial,sans-serif;background:#0a0d14;color:#dde1ea;
     direction:rtl;padding:24px;min-height:100vh}}
.header{{background:linear-gradient(135deg,#111827,#0d3b8c);border-radius:14px;
         padding:24px 32px;margin-bottom:20px;border:1px solid #1e3a8a;
         display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px}}
.header h1{{font-size:22px;color:#fff}}
.header p{{color:#93c5fd;font-size:12px;margin-top:4px}}
.back{{color:#60a5fa;font-size:13px;text-decoration:none;border:1px solid #1e3a8a;
       padding:8px 16px;border-radius:8px;white-space:nowrap}}
.back:hover{{background:#1e3a8a}}
.stats{{display:flex;gap:12px;margin-bottom:20px;flex-wrap:wrap}}
.stat{{background:#141928;border:1px solid #1e2d47;border-radius:12px;
       padding:14px 20px;flex:1;min-width:130px;text-align:center}}
.stat .n{{font-size:28px;font-weight:700;color:#60a5fa}}
.stat .l{{font-size:11px;color:#64748b;margin-top:3px}}
.hint{{font-size:11px;color:#475569;margin-bottom:12px}}
table{{width:100%;border-collapse:collapse;background:#111827;border-radius:12px;
       overflow:hidden;border:1px solid #1e293b}}
thead th{{background:#0d3b8c;padding:11px 14px;font-size:12px;font-weight:600;
          color:#dbeafe;text-align:right}}
tbody tr{{border-bottom:1px solid #1e293b;transition:background .12s}}
tbody tr:not(.drow):hover{{background:#1a2540}}
td{{padding:11px 14px;font-size:12px;vertical-align:top}}
.jtitle{{color:#60a5fa;text-decoration:none;font-weight:600;font-size:13px}}
.jtitle:hover{{text-decoration:underline}}
.company{{color:#94a3b8;font-size:12px}}
.comp-link{{color:#94a3b8;text-decoration:none}}
.comp-link:hover{{color:#60a5fa}}
.badge{{display:inline-block;padding:3px 9px;border-radius:20px;font-size:11px;font-weight:700}}
.badge-high{{background:#052e16;color:#4ade80;border:1px solid #166534}}
.badge-mid{{background:#431407;color:#fb923c;border:1px solid #9a3412}}
.badge-low{{background:#1e293b;color:#64748b;border:1px solid #334155}}
.kpi{{display:inline-block;padding:2px 7px;border-radius:6px;font-size:11px;font-weight:600;margin:2px 1px}}
.kpi-green{{background:#052e16;color:#4ade80;border:1px solid #166534}}
.kpi-orange{{background:#431407;color:#fb923c;border:1px solid #9a3412}}
.kpi-red{{background:#450a0a;color:#f87171;border:1px solid #991b1b}}
.kpi-purple{{background:#3b0764;color:#e879f9;border:1px solid #6b21a8}}
.kpi-gray{{background:#1e293b;color:#64748b;border:1px solid #334155}}
.kc{{white-space:nowrap;vertical-align:top}}
.drow td{{background:#0f172a;padding:0}}
.dgrid{{display:grid;grid-template-columns:1fr 1fr;border-top:1px solid #1e3a8a}}
.dbox{{padding:16px 20px;border-left:1px solid #1e293b}}
.dbox:last-child{{border-left:none}}
.dlabel{{font-size:11px;font-weight:700;color:#60a5fa;margin-bottom:8px;
         text-transform:uppercase;letter-spacing:.5px}}
.dtext{{font-size:12px;color:#94a3b8;line-height:1.65}}
.more{{display:inline-block;margin-top:8px;font-size:11px;color:#3b82f6;text-decoration:none}}
.more:hover{{text-decoration:underline}}
.footer{{margin-top:20px;text-align:center;font-size:11px;color:#334155}}
</style></head>
<body>
<div class="header">
  <div>
    <h1>🔍 {job_title} — {location}</h1>
    <p>{now} &nbsp;|&nbsp; זמן סריקה: {elapsed} &nbsp;|&nbsp; {'<span style="color:#4ade80">📄 ניקוד מותאם לרזומה</span>' if has_resume else 'ניקוד גנרי'} &nbsp;|&nbsp; נבנה עם Claude Code</p>
  </div>
  <a href="/" class="back">← סריקה חדשה</a>
</div>
<div class="stats">
  <div class="stat"><div class="n">{len(jobs)}</div><div class="l">משרות נמצאו</div></div>
  <div class="stat"><div class="n">{len(high_match)}</div><div class="l">התאמה גבוהה 70%+</div></div>
  <div class="stat"><div class="n">{len([j for j in jobs if j.get('applicants_n',-1) != -1 and j['applicants_n'] <= 25])}</div><div class="l">מתחת ל-25 מגישים</div></div>
  <div class="stat"><div class="n">{len([j for j in jobs if j.get('days_posted',-1) != -1 and j['days_posted'] <= 7])}</div><div class="l">פורסמו השבוע</div></div>
</div>
<p class="hint">💡 לחץ על שורה לפרטי המשרה והחברה</p>
<table>
  <thead><tr>
    <th>משרה</th><th>חברה</th><th>מיקום</th><th>התאמה</th>
    <th>🏁 תחרות</th><th>📋 פרטים</th>
  </tr></thead>
  <tbody>{rows}</tbody>
</table>
<div class="footer">
  נבנה על ידי <a href="https://www.instagram.com/dreamshot.ai.studio/" target="_blank"
  style="color:#818cf8;text-decoration:none">Moshe Schwartz · Dreamshot AI Studio</a>
  &nbsp;|&nbsp; נבנה עם Claude Code · Anthropic
</div>
<script>
function toggle(id){{
  const r=document.getElementById(id);
  r.style.display=r.style.display==='none'?'table-row':'none';
}}
</script>
</body></html>"""


PROGRESS_PAGE = """<!DOCTYPE html>
<html dir="rtl" lang="he">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>סורק... | Dreamshot AI</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Segoe UI',Arial,sans-serif;background:#0a0d14;color:#dde1ea;
     min-height:100vh;display:flex;flex-direction:column;align-items:center;
     justify-content:center;padding:24px;direction:rtl}
.card{background:#111827;border:1px solid #1e3a8a;border-radius:20px;
      padding:36px 40px;max-width:580px;width:100%}
h2{font-size:20px;color:#fff;margin-bottom:6px}
.sub{color:#64748b;font-size:13px;margin-bottom:24px}
.log{background:#0a0d14;border:1px solid #1e293b;border-radius:10px;
     padding:16px;height:280px;overflow-y:auto;font-family:monospace;
     font-size:12px;color:#94a3b8;line-height:1.8}
.log .ok{color:#4ade80}
.log .info{color:#60a5fa}
.bar{width:100%;height:6px;background:#1e293b;border-radius:3px;margin:16px 0}
.bar-fill{height:100%;background:linear-gradient(90deg,#1d4ed8,#3b82f6);
          border-radius:3px;transition:width .5s;width:5%}
.status{font-size:13px;color:#64748b;text-align:center;margin-top:8px}
</style>
</head>
<body>
<div class="card">
  <h2>⏳ סורק לינקדאין...</h2>
  <p class="sub">מחפש "{{ job }}" ב-{{ loc }}</p>
  <div class="log" id="log"></div>
  <div class="bar"><div class="bar-fill" id="bar"></div></div>
  <p class="status" id="status">מאתחל...</p>
</div>
<script>
const scanId = "{{ scan_id }}";
let lines = 0;
function poll() {
  fetch('/status/' + scanId)
  .then(r=>r.json())
  .then(d=>{
    const log = document.getElementById('log');
    const newLines = d.log.slice(lines);
    newLines.forEach(l=>{
      const div = document.createElement('div');
      div.className = l.startsWith('✅') ? 'ok' : l.startsWith('🔍') ? 'info' : '';
      div.textContent = l;
      log.appendChild(div);
    });
    if (newLines.length) log.scrollTop = log.scrollHeight;
    lines = d.log.length;
    const pct = Math.min(5 + (lines / 80) * 90, 95);
    document.getElementById('bar').style.width = pct + '%';
    document.getElementById('status').textContent = d.status_msg || 'סורק...';
    if (d.done) {
      document.getElementById('bar').style.width = '100%';
      setTimeout(()=>{ window.location.href = '/report/' + scanId; }, 800);
    } else {
      setTimeout(poll, 2000);
    }
  }).catch(()=>setTimeout(poll, 3000));
}
poll();
</script>
</body>
</html>"""


# ─── Routes ──────────────────────────────────────────────────────

@app.route("/")
def index():
    return LANDING


@app.route("/start", methods=["POST"])
def start():
    data        = request.get_json()
    job         = data.get("job", "").strip()[:80]
    loc         = data.get("loc", "Israel").strip()[:50]
    resume_b64  = data.get("resume_b64", "").strip()
    resume_name = data.get("resume_name", "").strip()
    resume_text = data.get("resume_text", "").strip()[:8000]

    if resume_b64 and resume_name:
        extracted = extract_text_from_file(resume_b64, resume_name)
        if extracted:
            resume_text = extracted[:8000]

    scan_id = str(uuid.uuid4())[:8]

    scans[scan_id] = {
        "job": job, "loc": loc, "resume": resume_text,
        "log": [], "done": False,
        "jobs": [], "started": datetime.now(),
        "status_msg": "מאתחל...",
    }

    def _run():
        def log_fn(msg):
            scans[scan_id]["log"].append(msg)
            scans[scan_id]["status_msg"] = msg[:60]
        try:
            jobs = run_scan(job, loc, log_fn=log_fn, resume_text=resume_text)
            scans[scan_id]["jobs"] = jobs
        except Exception as e:
            scans[scan_id]["log"].append(f"שגיאה: {e}")
        finally:
            scans[scan_id]["done"] = True
            scans[scan_id]["status_msg"] = "סיום!"

    threading.Thread(target=_run, daemon=True).start()
    return jsonify({"scan_id": scan_id})


@app.route("/scan/<scan_id>")
def scan_page(scan_id):
    s = scans.get(scan_id, {})
    return render_template_string(PROGRESS_PAGE,
                                  scan_id=scan_id,
                                  job=s.get("job", ""),
                                  loc=s.get("loc", ""))


@app.route("/status/<scan_id>")
def status(scan_id):
    s = scans.get(scan_id)
    if not s:
        return jsonify({"done": True, "log": [], "status_msg": "לא נמצא"})
    return jsonify({
        "done":       s["done"],
        "log":        s["log"],
        "status_msg": s.get("status_msg", ""),
    })


@app.route("/report/<scan_id>")
def report(scan_id):
    s = scans.get(scan_id)
    if not s or not s["done"]:
        return "הסריקה עדיין רצה...", 202
    elapsed = str(datetime.now() - s["started"]).split(".")[0]
    return build_report_html(s["jobs"], s["job"], s["loc"], elapsed,
                             has_resume=bool(s.get("resume", "").strip()))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
