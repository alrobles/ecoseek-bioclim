"""
EcoSeek Bioclim v2.0 — ERA5-Land bioclimatic variable server.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Dict, List

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

DATA_DIR = Path(os.environ.get("BIOCLIM_DATA_DIR", "/data"))
PORT = int(os.environ.get("BIOCLIM_PORT", "8650"))
BASE_URL = "https://bioclim.ecoseek.org"

BIOCLIM_VARS = {
    "bio01": "Annual Mean Temperature",
    "bio02": "Mean Diurnal Range",
    "bio03": "Isothermality",
    "bio04": "Temperature Seasonality",
    "bio05": "Max Temp Warmest Month",
    "bio06": "Min Temp Coldest Month",
    "bio07": "Temperature Annual Range",
    "bio08": "Mean Temp Wettest Quarter",
    "bio09": "Mean Temp Driest Quarter",
    "bio10": "Mean Temp Warmest Quarter",
    "bio11": "Mean Temp Coldest Quarter",
    "bio12": "Annual Precipitation",
    "bio13": "Precip Wettest Month",
    "bio14": "Precip Driest Month",
    "bio15": "Precip Seasonality (CV)",
    "bio16": "Precip Wettest Quarter",
    "bio17": "Precip Driest Quarter",
    "bio18": "Precip Warmest Quarter",
    "bio19": "Precip Coldest Quarter",
}
TEMP_VARS = {k: v for k, v in BIOCLIM_VARS.items() if int(k.replace("bio", "")) <= 11}
PRECIP_VARS = {k: v for k, v in BIOCLIM_VARS.items() if int(k.replace("bio", "")) >= 12}

app = FastAPI(title="EcoSeek Bioclim", version="2.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
STATIC_DIR = Path(__file__).parent.parent / "frontend" / "public"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


def _scan_years() -> Dict[str, List[str]]:
    result = {}
    if not DATA_DIR.exists():
        return result
    for year_dir in sorted(DATA_DIR.iterdir()):
        if year_dir.is_dir() and re.match(r"^\d{4}$", year_dir.name):
            tifs = sorted(f.name for f in year_dir.glob("*.tif"))
            if tifs:
                result[year_dir.name] = tifs
    return result


def _file_size_human(path: Path) -> str:
    size = path.stat().st_size
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


# ── v2.0 Design System ─────────────────────────────────────────────────────
CSS_V2 = """
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600&display=swap');

  :root {
    --green-50: #f0fdf4; --green-100: #dcfce7; --green-200: #bbf7d0;
    --green-500: #22c55e; --green-600: #16a34a; --green-700: #15803d;
    --green-800: #166534; --green-900: #14532d; --green-950: #052e16;
    --primary: #166534; --primary-light: #dcfce7; --primary-dark: #052e16;
    --bg: #fafafa; --bg-card: #ffffff; --text: #171717;
    --text-muted: #737373; --border: #e5e5e5;
    --radius: 12px; --radius-lg: 16px;
    --shadow-sm: 0 1px 2px rgba(0,0,0,0.05);
    --shadow: 0 1px 3px rgba(0,0,0,0.1), 0 1px 2px rgba(0,0,0,0.06);
    --shadow-md: 0 4px 6px rgba(0,0,0,0.07), 0 2px 4px rgba(0,0,0,0.06);
    --shadow-lg: 0 10px 15px rgba(0,0,0,0.1), 0 4px 6px rgba(0,0,0,0.05);
    --font: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    --mono: 'JetBrains Mono', 'SF Mono', Monaco, monospace;
    --transition: 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  }

  [data-theme="dark"] {
    --bg: #0a0a0a; --bg-card: #171717; --text: #fafafa;
    --text-muted: #a3a3a3; --border: #262626;
    --primary: #22c55e; --primary-light: #14532d; --primary-dark: #052e16;
    --shadow-sm: 0 1px 2px rgba(0,0,0,0.3);
    --shadow: 0 1px 3px rgba(0,0,0,0.4), 0 1px 2px rgba(0,0,0,0.3);
    --shadow-md: 0 4px 6px rgba(0,0,0,0.3), 0 2px 4px rgba(0,0,0,0.2);
    --shadow-lg: 0 10px 15px rgba(0,0,0,0.4), 0 4px 6px rgba(0,0,0,0.3);
  }

  * { margin: 0; padding: 0; box-sizing: border-box; }
  html { scroll-behavior: smooth; }
  body {
    font-family: var(--font); background: var(--bg); color: var(--text);
    line-height: 1.6; transition: background var(--transition), color var(--transition);
    -webkit-font-smoothing: antialiased;
  }
  a { color: var(--primary); text-decoration: none; transition: opacity var(--transition); }
  a:hover { opacity: 0.8; }

  /* ── Nav ── */
  .nav {
    position: sticky; top: 0; z-index: 100;
    background: var(--bg-card); border-bottom: 1px solid var(--border);
    backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);
    background: color-mix(in srgb, var(--bg-card) 85%, transparent);
  }
  .nav-inner {
    max-width: 960px; margin: 0 auto; padding: 0.8rem 1.5rem;
    display: flex; align-items: center; justify-content: space-between;
  }
  .nav-brand { display: flex; align-items: center; gap: 0.6rem; font-weight: 700; font-size: 1rem; }
  .nav-brand img { width: 28px; height: 28px; }
  .nav-links { display: flex; align-items: center; gap: 1.5rem; font-size: 0.85rem; }
  .nav-links a { color: var(--text-muted); font-weight: 500; }
  .nav-links a:hover { color: var(--text); opacity: 1; }
  .theme-toggle {
    background: none; border: 1px solid var(--border); border-radius: 8px;
    padding: 0.35rem 0.5rem; cursor: pointer; font-size: 1rem;
    color: var(--text-muted); transition: all var(--transition);
  }
  .theme-toggle:hover { border-color: var(--primary); color: var(--primary); }

  /* ── Hero ── */
  .hero {
    text-align: center; padding: 4rem 1.5rem 3rem;
    position: relative; overflow: hidden;
  }
  .hero::before {
    content: ''; position: absolute; top: -50%; left: -50%;
    width: 200%; height: 200%;
    background: radial-gradient(circle at 30% 40%, color-mix(in srgb, var(--primary) 8%, transparent) 0%, transparent 50%),
                radial-gradient(circle at 70% 60%, color-mix(in srgb, var(--primary) 5%, transparent) 0%, transparent 50%);
    animation: heroGlow 20s ease-in-out infinite alternate;
  }
  @keyframes heroGlow {
    0% { transform: translate(0, 0) rotate(0deg); }
    100% { transform: translate(-5%, -5%) rotate(3deg); }
  }
  .hero > * { position: relative; }
  .hero img { width: 72px; height: 72px; margin-bottom: 1.2rem; }
  .hero h1 {
    font-size: clamp(2rem, 5vw, 3.2rem); font-weight: 900;
    letter-spacing: -0.03em; line-height: 1.1; margin-bottom: 0.5rem;
  }
  .hero .subtitle {
    font-size: 1.1rem; color: var(--text-muted); font-weight: 400;
    max-width: 500px; margin: 0 auto;
  }

  /* ── Stats ── */
  .stats {
    display: flex; justify-content: center; gap: 3rem;
    padding: 2rem 1rem 1rem; flex-wrap: wrap;
  }
  .stat { text-align: center; }
  .stat .num {
    font-size: 2rem; font-weight: 800; color: var(--primary);
    letter-spacing: -0.02em; font-variant-numeric: tabular-nums;
  }
  .stat .lbl { font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.08em; font-weight: 600; }

  /* ── Container ── */
  .container { max-width: 720px; margin: 0 auto; padding: 0 1.5rem; }

  /* ── Cards ── */
  .card {
    background: var(--bg-card); border: 1px solid var(--border);
    border-radius: var(--radius-lg); padding: 1.5rem;
    margin: 1.2rem 0; box-shadow: var(--shadow-sm);
    transition: box-shadow var(--transition), border-color var(--transition);
  }
  .card:hover { box-shadow: var(--shadow-md); border-color: color-mix(in srgb, var(--primary) 30%, var(--border)); }
  .card h2 {
    font-size: 0.85rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.06em; color: var(--text-muted); margin-bottom: 1rem;
  }

  /* ── Quick Download ── */
  .quick-row {
    display: flex; gap: 0.6rem; align-items: center;
  }
  .year-input {
    width: 100px; padding: 0.7rem 1rem; font-size: 1rem; font-weight: 600;
    font-family: var(--mono);
    border: 2px solid var(--border); border-radius: var(--radius);
    background: var(--bg); color: var(--text); text-align: center;
    transition: border-color var(--transition);
  }
  .year-input:focus { border-color: var(--primary); outline: none; }
  .btn {
    padding: 0.7rem 1.5rem; border: none; border-radius: var(--radius);
    font-size: 0.9rem; font-weight: 600; cursor: pointer;
    transition: all var(--transition); font-family: var(--font);
  }
  .btn-primary { background: var(--primary); color: white; }
  .btn-primary:hover { filter: brightness(1.1); transform: translateY(-1px); box-shadow: var(--shadow-md); }
  .btn-outline {
    background: transparent; color: var(--primary);
    border: 2px solid var(--primary);
  }
  .btn-outline:hover { background: var(--primary); color: white; transform: translateY(-1px); }
  .btn-ghost { background: transparent; color: var(--text-muted); border: 1px solid var(--border); }
  .btn-ghost:hover { border-color: var(--primary); color: var(--primary); }

  /* ── Range ── */
  .range-row { display: flex; align-items: center; gap: 0.8rem; margin-bottom: 0.4rem; }
  .range-row label { min-width: 2.5rem; font-weight: 600; font-size: 0.8rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; }
  .range-row input[type=range] { flex: 1; accent-color: var(--primary); height: 4px; }
  .range-val {
    min-width: 3rem; text-align: center; font-weight: 800;
    font-size: 1.2rem; color: var(--primary); font-family: var(--mono);
  }
  .range-meta {
    font-size: 0.82rem; color: var(--text-muted); margin: 0.6rem 0 1rem;
    font-variant-numeric: tabular-nums;
  }

  /* ── Terminal ── */
  .terminal {
    background: #1a1a2e; border-radius: var(--radius); padding: 1rem 1.2rem;
    font-family: var(--mono); font-size: 0.82rem; color: #e2e8f0;
    overflow-x: auto; position: relative; line-height: 1.7;
    border: 1px solid #2d2d44;
  }
  .terminal::before {
    content: '● ● ●'; position: absolute; top: 0.5rem; left: 0.8rem;
    font-size: 0.6rem; color: #4a4a6a; letter-spacing: 0.3rem;
  }
  .terminal .prompt { color: #22c55e; }
  .terminal .flag { color: #60a5fa; }
  .terminal .url { color: #a78bfa; }
  .terminal .str { color: #fbbf24; }
  .terminal-cmd { padding-top: 1rem; }

  .range-actions { display: flex; gap: 0.6rem; margin-top: 1rem; flex-wrap: wrap; }

  /* ── Var grid ── */
  .var-grid {
    display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 0.5rem; margin-top: 0.5rem;
  }
  .var-chip {
    display: flex; align-items: center; gap: 0.5rem;
    padding: 0.5rem 0.7rem; border-radius: 8px; font-size: 0.8rem;
    background: var(--green-50); border: 1px solid var(--green-200);
    transition: all var(--transition);
  }
  [data-theme="dark"] .var-chip { background: var(--green-950); border-color: var(--green-900); }
  .var-chip:hover { transform: translateY(-1px); box-shadow: var(--shadow); }
  .var-chip code {
    font-weight: 700; color: var(--primary); font-family: var(--mono);
    font-size: 0.78rem; min-width: 3rem;
  }

  /* ── File list ── */
  .file-row {
    display: flex; align-items: center; padding: 0.7rem 0;
    border-bottom: 1px solid var(--border); gap: 0.8rem;
  }
  .file-row:last-child { border-bottom: none; }
  .file-name { font-family: var(--mono); font-weight: 500; font-size: 0.88rem; min-width: 12rem; }
  .file-desc { color: var(--text-muted); font-size: 0.82rem; flex: 1; }
  .file-size { color: var(--text-muted); font-size: 0.82rem; font-family: var(--mono); min-width: 4rem; text-align: right; }
  .dl-btn {
    background: var(--primary); color: white; padding: 0.3rem 0.7rem;
    border-radius: 6px; font-size: 0.78rem; font-weight: 600;
    transition: all var(--transition);
  }
  .dl-btn:hover { filter: brightness(1.1); transform: translateY(-1px); opacity: 1; }

  /* ── Footer ── */
  .footer {
    text-align: center; color: var(--text-muted); font-size: 0.78rem;
    padding: 3rem 1rem 2rem; border-top: 1px solid var(--border); margin-top: 3rem;
  }
  .footer a { margin: 0 0.3rem; }

  /* ── Responsive ── */
  @media (max-width: 640px) {
    .stats { gap: 1.5rem; }
    .stat .num { font-size: 1.5rem; }
    .quick-row { flex-direction: column; }
    .year-input { width: 100%; }
    .btn { width: 100%; }
    .range-actions { flex-direction: column; }
    .range-actions .btn { width: 100%; }
    .file-row { flex-wrap: wrap; }
    .file-desc { min-width: 100%; order: 3; }
  }
</style>
"""


def _nav(active: str = ""):
    return f"""
    <nav class="nav">
      <div class="nav-inner">
        <a href="/" class="nav-brand">
          <img src="/static/ecoseek-logo.svg" alt="EcoSeek">
          <span>Bioclim</span>
        </a>
        <div class="nav-links">
          <a href="/api/summary">API</a>
          <a href="https://github.com/alrobles/ecoseek-bioclim">GitHub</a>
          <a href="https://ecoseek.org">EcoSeek</a>
          <button class="theme-toggle" onclick="toggleTheme()" title="Toggle dark mode">◐</button>
        </div>
      </div>
    </nav>"""


THEME_JS = """
    function toggleTheme() {
      const t = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', t);
      localStorage.setItem('theme', t);
    }
    (function() {
      const t = localStorage.getItem('theme') || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
      document.documentElement.setAttribute('data-theme', t);
    })();
"""


# ── Landing page ────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
def index():
    data = _scan_years()
    years = sorted(data.keys())
    yr_min, yr_max = int(years[0]), int(years[-1])
    total = sum(len(f) for f in data.values())

    def var_chips(vars_dict):
        return "".join(
            f'<div class="var-chip"><code>{k}</code><span>{v}</span></div>'
            for k, v in vars_dict.items()
        )

    return HTMLResponse(f"""<!DOCTYPE html>
<html lang="en" data-theme="light">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EcoSeek Bioclim — ERA5-Land Bioclimatic Variables</title>
    <link rel="icon" type="image/svg+xml" href="/static/favicon.svg">
    {CSS_V2}
</head>
<body>
    {_nav()}

    <div class="hero">
        <img src="/static/ecoseek-logo.svg" alt="EcoSeek">
        <h1>EcoSeek Bioclim</h1>
        <p class="subtitle">ERA5-Land bioclimatic variables · BIO01-BIO19 · {yr_min}–{yr_max}</p>
    </div>

    <div class="stats">
        <div class="stat"><div class="num">{len(years)}</div><div class="lbl">Years</div></div>
        <div class="stat"><div class="num">19</div><div class="lbl">Variables</div></div>
        <div class="stat"><div class="num">{total}</div><div class="lbl">GeoTIFFs</div></div>
        <div class="stat"><div class="num">~9km</div><div class="lbl">Resolution</div></div>
    </div>

    <div class="container">
        <div class="card">
            <h2>Quick Download</h2>
            <div class="quick-row">
                <input type="number" class="year-input" id="yearInput"
                       min="{yr_min}" max="{yr_max}" value="{yr_max}"
                       onkeydown="if(event.key==='Enter')goToYear()">
                <button class="btn btn-primary" onclick="goToYear()">Browse Year →</button>
            </div>
        </div>

        <div class="card">
            <h2>Batch Download</h2>
            <div class="range-row">
                <label>From</label>
                <input type="range" id="rangeStart" min="{yr_min}" max="{yr_max}" value="{yr_min}" oninput="updateRange()">
                <span class="range-val" id="startVal">{yr_min}</span>
            </div>
            <div class="range-row">
                <label>To</label>
                <input type="range" id="rangeEnd" min="{yr_min}" max="{yr_max}" value="{yr_max}" oninput="updateRange()">
                <span class="range-val" id="endVal">{yr_max}</span>
            </div>
            <div class="range-meta">
                <span id="fileCount">{total}</span> files · <span id="yearCount">{len(years)}</span> years × 19 variables
            </div>

            <div class="terminal">
                <div class="terminal-cmd" id="curlCmd"></div>
            </div>

            <div class="range-actions">
                <button class="btn btn-primary" onclick="copyCurl()">Copy</button>
                <button class="btn btn-outline" onclick="downloadScript()">Download .sh</button>
                <button class="btn btn-ghost" onclick="downloadUrls()">URL list</button>
            </div>
        </div>

        <div class="card">
            <h2>🌡️ Temperature Variables</h2>
            <div class="var-grid">{var_chips(TEMP_VARS)}</div>
        </div>

        <div class="card">
            <h2>🌧️ Precipitation Variables</h2>
            <div class="var-grid">{var_chips(PRECIP_VARS)}</div>
        </div>

        <div class="card">
            <h2>API Endpoints</h2>
            <div style="font-family:var(--mono);font-size:0.82rem;line-height:2.2">
                <div><span style="color:var(--primary);font-weight:700">GET</span> <a href="/api/summary">/api/summary</a></div>
                <div><span style="color:var(--primary);font-weight:700">GET</span> <a href="/api/years">/api/years</a></div>
                <div><span style="color:var(--primary);font-weight:700">GET</span> <a href="/api/variables">/api/variables</a></div>
                <div><span style="color:var(--primary);font-weight:700">GET</span> /api/download/{{year}}/{{file}}</div>
                <div><span style="color:var(--primary);font-weight:700">GET</span> /api/scripts?start=X&amp;end=Y&amp;fmt=bash</div>
            </div>
        </div>
    </div>

    <div class="footer">
        <a href="https://ecoseek.org">EcoSeek</a> ·
        <a href="https://cds.climate.copernicus.eu">ERA5-Land</a> ·
        <a href="https://github.com/alrobles/xclim">xclim</a> ·
        <a href="https://github.com/alrobles/ecoseek-bioclim">Source</a>
    </div>

    <script>
    {THEME_JS}

    const yrMin = {yr_min}, yrMax = {yr_max};

    function goToYear() {{
      const y = document.getElementById('yearInput').value;
      if (y >= yrMin && y <= yrMax) window.location.href = '/' + y + '/';
    }}

    function updateRange() {{
      let s = parseInt(document.getElementById('rangeStart').value);
      let e = parseInt(document.getElementById('rangeEnd').value);
      if (s > e) {{ document.getElementById('rangeEnd').value = s; e = s; }}
      document.getElementById('startVal').textContent = s;
      document.getElementById('endVal').textContent = e;
      const n = e - s + 1;
      document.getElementById('fileCount').textContent = n * 19;
      document.getElementById('yearCount').textContent = n;
      updateCurl();
    }}

    function updateCurl() {{
      const s = document.getElementById('rangeStart').value;
      const e = document.getElementById('rangeEnd').value;
      const url = window.location.origin + '/api/scripts?start=' + s + '&end=' + e + '&fmt=bash';
      document.getElementById('curlCmd').innerHTML =
        '<span class="prompt">$ </span>curl -sSf <span class="str">"' + url + '"</span> <span class="flag">-o</span> bioclim.sh && bash bioclim.sh';
    }}

    function copyCurl() {{
      const s = document.getElementById('rangeStart').value;
      const e = document.getElementById('rangeEnd').value;
      const url = window.location.origin + '/api/scripts?start=' + s + '&end=' + e + '&fmt=bash';
      navigator.clipboard.writeText('curl -sSf "' + url + '" -o bioclim.sh && bash bioclim.sh');
    }}

    function downloadScript() {{
      const s = document.getElementById('rangeStart').value;
      const e = document.getElementById('rangeEnd').value;
      window.location.href = '/api/scripts?start=' + s + '&end=' + e + '&fmt=bash&download=bioclim_' + s + '-' + e + '.sh';
    }}

    function downloadUrls() {{
      const s = document.getElementById('rangeStart').value;
      const e = document.getElementById('rangeEnd').value;
      window.location.href = '/api/scripts?start=' + s + '&end=' + e + '&fmt=urls&download=bioclim_urls_' + s + '-' + e + '.txt';
    }}

    updateCurl();
    </script>
</body>
</html>""")


# ── Year browser ────────────────────────────────────────────────────────────
@app.get("/{year}/", response_class=HTMLResponse)
def year_browser(year: str):
    year_dir = DATA_DIR / year
    if not year_dir.exists() or not re.match(r"^\d{4}$", year):
        raise HTTPException(status_code=404, detail="Year not found")
    files = sorted(f.name for f in year_dir.glob("*.tif"))
    if not files:
        raise HTTPException(status_code=404, detail="No files")

    rows = ""
    for fn in files:
        var_code = fn.split("_")[0]
        desc = BIOCLIM_VARS.get(var_code, "")
        size = _file_size_human(year_dir / fn)
        rows += f"""
        <div class="file-row">
            <span class="file-name"><a href="/{year}/{fn}">{fn}</a></span>
            <span class="file-desc">{desc}</span>
            <span class="file-size">{size}</span>
            <a href="/api/download/{year}/{fn}" class="dl-btn">↓ .tif</a>
        </div>"""

    return HTMLResponse(f"""<!DOCTYPE html>
<html lang="en" data-theme="light">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EcoSeek Bioclim — {year}</title>
    <link rel="icon" type="image/svg+xml" href="/static/favicon.svg">
    {CSS_V2}
</head>
<body>
    {_nav()}
    <div class="hero" style="padding:3rem 1.5rem 2rem">
        <img src="/static/ecoseek-logo.svg" alt="EcoSeek" style="width:56px;height:56px">
        <h1>Year {year}</h1>
        <p class="subtitle">BIO01-BIO19 · ERA5-Land · {len(files)} files</p>
    </div>
    <div class="container">
        <a href="/" style="display:inline-block;padding:0.5rem 0;font-size:0.9rem">← All years</a>
        <div class="card">
            <h2>Files</h2>
            {rows}
        </div>
    </div>
    <div class="footer">
        <a href="https://ecoseek.org">EcoSeek</a> ·
        <a href="https://cds.climate.copernicus.eu">ERA5-Land</a> ·
        <a href="https://github.com/alrobles/xclim">xclim</a> ·
        <a href="https://github.com/alrobles/ecoseek-bioclim">Source</a>
    </div>
    <script>{THEME_JS}</script>
</body>
</html>""")


# ── API ─────────────────────────────────────────────────────────────────────
@app.get("/api/years")
def list_years():
    data = _scan_years()
    return {"years": sorted(data.keys()), "count": len(data)}

@app.get("/api/variables")
def list_variables():
    return {"variables": BIOCLIM_VARS}

@app.get("/api/summary")
def summary():
    data = _scan_years()
    inventory = {}
    for year, files in data.items():
        vars_in_year = sorted(set(f.split("_")[0] for f in files if f.endswith(".tif")))
        inventory[year] = {"count": len(files), "variables": vars_in_year}
    return {
        "source": "ERA5-Land", "spatial_resolution": "~0.1° (~9km)",
        "temporal_coverage": f"{min(data.keys())}-{max(data.keys())}" if data else "N/A",
        "variables": BIOCLIM_VARS, "years": inventory,
        "total_files": sum(len(f) for f in data.values()),
    }

@app.get("/api/download/{year}/{filename}")
def download_file(year: str, filename: str):
    filepath = DATA_DIR / year / filename
    if not filepath.exists() or not filepath.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(filepath, media_type="image/tiff", filename=filename)

@app.get("/api/scripts")
def generate_scripts(start: int = Query(1980), end: int = Query(2020), fmt: str = Query("bash"), download: str = Query(None)):
    script = _dl_script(start, end, fmt)
    if download:
        return PlainTextResponse(script, headers={"Content-Disposition": f'attachment; filename="{download}"'})
    return PlainTextResponse(script)

@app.get("/{year}/{filename}")
def direct_download(year: str, filename: str):
    filepath = DATA_DIR / year / filename
    if not filepath.exists() or not filepath.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    if not re.match(r"^bio\d{2}_\d{4}\.tif$", filename):
        raise HTTPException(status_code=400, detail="Invalid filename")
    return FileResponse(filepath, media_type="image/tiff", filename=filename)


def _dl_script(start: int, end: int, fmt: str) -> str:
    years = _scan_years()
    valid = [y for y in years if start <= int(y) <= end]
    lines = []
    if fmt == "bash":
        lines.append(f"#!/bin/bash")
        lines.append(f"# EcoSeek Bioclim — ERA5-Land BIO01-BIO19 ({start}-{end})")
        lines.append(f"# {len(valid)} years × 19 variables = {len(valid)*19} files")
        lines.append(f"set -e\ncd \"$(mktemp -d)\"")
        for y in valid:
            lines.append(f"mkdir -p {y}")
            for v in BIOCLIM_VARS:
                lines.append(f"curl -sSfO {BASE_URL}/api/download/{y}/{v}_{y}.tif")
        lines.append(f'\necho "Done: {len(valid)*19} files in $(pwd)"')
    elif fmt == "urls":
        for y in valid:
            for v in BIOCLIM_VARS:
                lines.append(f"{BASE_URL}/api/download/{y}/{v}_{y}.tif")
    return "\n".join(lines)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
