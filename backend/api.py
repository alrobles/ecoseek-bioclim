"""
EcoSeek Bioclim — ERA5-Land bioclimatic variable server.
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

app = FastAPI(title="EcoSeek Bioclim", version="1.0.0")
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


CSS = """
<style>
    :root {
        --primary: #1B5E20; --primary-light: #E8F5E9; --primary-dark: #154215;
        --bg: #FFFFFF; --card: #FFFFFF; --text: #212121;
        --text-muted: #757575; --border: #E0E0E0;
    }
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        background: var(--bg); color: var(--text); line-height: 1.6;
    }
    a { color: var(--primary); text-decoration: none; }
    a:hover { text-decoration: underline; }

    .hero {
        text-align: center; padding: 3rem 1rem 2rem;
        border-bottom: 1px solid var(--border);
    }
    .hero img { width: 64px; height: 64px; margin-bottom: 1rem; }
    .hero h1 { font-size: 1.8rem; font-weight: 700; margin-bottom: 0.3rem; }
    .hero p { color: var(--text-muted); font-size: 1rem; }

    .stats {
        display: flex; justify-content: center; gap: 2rem;
        padding: 1.5rem 1rem; flex-wrap: wrap;
    }
    .stat { text-align: center; }
    .stat .num { font-size: 1.5rem; font-weight: 700; color: var(--primary); }
    .stat .lbl { font-size: 0.8rem; color: var(--text-muted); }

    .container { max-width: 720px; margin: 0 auto; padding: 0 1rem; }

    /* Quick access */
    .quick-access {
        display: flex; gap: 0.8rem; align-items: center;
        padding: 1.5rem 0; justify-content: center;
    }
    .year-input {
        width: 100px; padding: 0.6rem 0.8rem; font-size: 1rem;
        border: 2px solid var(--border); border-radius: 8px;
        text-align: center; font-weight: 600;
    }
    .year-input:focus { border-color: var(--primary); outline: none; }
    .go-btn {
        padding: 0.6rem 1.5rem; background: var(--primary); color: white;
        border: none; border-radius: 8px; font-size: 1rem; font-weight: 600;
        cursor: pointer;
    }
    .go-btn:hover { background: var(--primary-dark); }

    /* Range section */
    .section {
        background: var(--card); border: 1px solid var(--border);
        border-radius: 12px; padding: 1.5rem; margin: 1rem 0;
    }
    .section h2 {
        font-size: 1rem; font-weight: 600; margin-bottom: 1rem;
        color: var(--primary);
    }

    /* Slider */
    .range-row {
        display: flex; align-items: center; gap: 1rem; margin-bottom: 0.5rem;
    }
    .range-row label { min-width: 3rem; font-weight: 600; font-size: 0.9rem; }
    .range-row input[type=range] {
        flex: 1; accent-color: var(--primary); height: 6px;
    }
    .range-val {
        min-width: 3rem; text-align: center; font-weight: 700;
        font-size: 1.1rem; color: var(--primary);
    }
    .range-actions {
        display: flex; gap: 0.8rem; margin-top: 1rem; flex-wrap: wrap;
    }
    .action-btn {
        padding: 0.5rem 1.2rem; border: 2px solid var(--primary);
        border-radius: 8px; background: white; color: var(--primary);
        font-size: 0.9rem; font-weight: 600; cursor: pointer;
    }
    .action-btn:hover { background: var(--primary); color: white; }
    .action-btn.primary { background: var(--primary); color: white; }
    .action-btn.primary:hover { background: var(--primary-dark); }

    /* Download box */
    .dl-box {
        background: #f8fafc; border: 1px solid var(--border);
        border-radius: 8px; padding: 1rem; margin-top: 1rem;
        font-family: 'SF Mono', Monaco, monospace; font-size: 0.82rem;
        color: #334155; overflow-x: auto; white-space: pre-wrap;
        display: none; line-height: 1.8;
    }
    .dl-box .comment { color: #94a3b8; }
    .dl-box .cmd { color: var(--primary); font-weight: 600; }

    /* Tabs */
    .tabs { display: flex; gap: 0; margin-bottom: 0; }
    .tab-btn {
        padding: 0.5rem 1rem; border: 1px solid var(--border);
        background: #f8fafc; cursor: pointer; font-size: 0.85rem;
        font-weight: 500; color: var(--text-muted);
    }
    .tab-btn:first-child { border-radius: 8px 0 0 0; }
    .tab-btn:last-child { border-radius: 0 8px 0 0; }
    .tab-btn.active {
        background: white; border-bottom-color: white;
        color: var(--primary); font-weight: 600;
    }

    /* Variables */
    .var-grid {
        display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
        gap: 0.5rem; margin-top: 0.8rem;
    }
    .var-card {
        display: flex; align-items: center; gap: 0.5rem;
        padding: 0.5rem 0.6rem; background: var(--primary-light);
        border-radius: 6px; font-size: 0.82rem;
    }
    .var-code { font-weight: 700; color: var(--primary); font-family: monospace; min-width: 3rem; }

    /* File list (year page) */
    .file-row {
        display: flex; align-items: center; justify-content: space-between;
        padding: 0.6rem 0; border-bottom: 1px solid var(--border);
    }
    .file-row:last-child { border-bottom: none; }
    .file-name { font-family: monospace; font-weight: 500; }
    .file-desc { color: var(--text-muted); font-size: 0.85rem; flex: 1; margin: 0 1rem; }
    .file-size { color: var(--text-muted); font-size: 0.85rem; min-width: 5rem; text-align: right; }
    .dl-btn {
        background: var(--primary); color: white; padding: 0.3rem 0.8rem;
        border-radius: 6px; font-size: 0.8rem; font-weight: 500; margin-left: 1rem;
    }
    .dl-btn:hover { background: var(--primary-dark); text-decoration: none; }
    .back-link { display: inline-block; padding: 0.8rem 0; color: var(--primary); font-size: 0.9rem; }

    .footer {
        text-align: center; color: var(--text-muted); font-size: 0.8rem;
        padding: 2rem 1rem; border-top: 1px solid var(--border); margin-top: 2rem;
    }
</style>
"""


def _dl_script(start: int, end: int, fmt: str) -> str:
    """Generate download script for a year range."""
    years = _scan_years()
    valid = [y for y in years if start <= int(y) <= end]
    lines = []

    if fmt == "bash":
        lines.append(f"# EcoSeek Bioclim — ERA5-Land BIO01-BIO19 ({start}-{end})")
        lines.append(f"# {len(valid)} years × 19 variables = {len(valid)*19} files")
        lines.append("")
        lines.append(f"mkdir -p ecoseek-bioclim && cd ecoseek-bioclim")
        for y in valid:
            lines.append(f"mkdir -p {y}")
            for v in BIOCLIM_VARS:
                lines.append(f"curl -sO {BASE_URL}/api/download/{y}/{v}_{y}.tif")
        lines.append("")
        lines.append(f'echo "Downloaded {len(valid)*19} files"')
    elif fmt == "powershell":
        lines.append(f"# EcoSeek Bioclim — ERA5-Land BIO01-BIO19 ({start}-{end})")
        lines.append(f"New-Item -ItemType Directory -Force -Path ecoseek-bioclim | Out-Null")
        for y in valid:
            lines.append(f"New-Item -ItemType Directory -Force -Path ecoseek-bioclim\\{y} | Out-Null")
            for v in BIOCLIM_VARS:
                lines.append(f"Invoke-WebRequest -Uri {BASE_URL}/api/download/{y}/{v}_{y}.tif -OutFile ecoseek-bioclim\\{y}\\{v}_{y}.tif")
    elif fmt == "python":
        lines.append("# EcoSeek Bioclim — ERA5-Land BIO01-BIO19")
        lines.append("from ecoseek_bioclim import BioclimClient")
        lines.append("")
        lines.append(f"client = BioclimClient()")
        lines.append(f"client.download_all('./ecoseek-bioclim', years={list(range(start, end+1))})")
    elif fmt == "urls":
        for y in valid:
            for v in BIOCLIM_VARS:
                lines.append(f"{BASE_URL}/api/download/{y}/{v}_{y}.tif")

    return "\n".join(lines)


# ── Landing page ────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
def index():
    data = _scan_years()
    years = sorted(data.keys())
    yr_min = int(years[0]) if years else 1980
    yr_max = int(years[-1]) if years else 2020
    total = sum(len(f) for f in data.values())

    def var_cards(vars_dict):
        return "".join(
            f'<div class="var-card"><span class="var-code">{k}</span>{v}</div>'
            for k, v in vars_dict.items()
        )

    return HTMLResponse(f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EcoSeek Bioclim — ERA5-Land Bioclimatic Variables</title>
    <link rel="icon" type="image/svg+xml" href="/static/favicon.svg">
    {CSS}
</head>
<body>
    <div class="hero">
        <img src="/static/ecoseek-logo.svg" alt="EcoSeek">
        <h1>EcoSeek Bioclim</h1>
        <p>ERA5-Land bioclimatic variables · BIO01-BIO19 · {yr_min}–{yr_max}</p>
    </div>

    <div class="stats">
        <div class="stat"><div class="num">{len(years)}</div><div class="lbl">Years</div></div>
        <div class="stat"><div class="num">19</div><div class="lbl">Variables</div></div>
        <div class="stat"><div class="num">{total}</div><div class="lbl">GeoTIFFs</div></div>
        <div class="stat"><div class="num">~9km</div><div class="lbl">Resolution</div></div>
    </div>

    <div class="container">
        <!-- Quick access -->
        <div class="section">
            <h2>📥 Quick Download</h2>
            <div class="quick-access">
                <label style="font-size:0.9rem;color:var(--text-muted)">Year</label>
                <input type="number" class="year-input" id="yearInput"
                       min="{yr_min}" max="{yr_max}" value="{yr_max}">
                <button class="go-btn" onclick="goToYear()">Browse →</button>
            </div>
        </div>

        <!-- Range download -->
        <div class="section">
            <h2>📦 Batch Download</h2>
            <div class="range-row">
                <label>From</label>
                <input type="range" id="rangeStart" min="{yr_min}" max="{yr_max}" value="{yr_min}"
                       oninput="updateRange()">
                <span class="range-val" id="startVal">{yr_min}</span>
            </div>
            <div class="range-row">
                <label>To</label>
                <input type="range" id="rangeEnd" min="{yr_min}" max="{yr_max}" value="{yr_max}"
                       oninput="updateRange()">
                <span class="range-val" id="endVal">{yr_max}</span>
            </div>
            <p style="font-size:0.85rem;color:var(--text-muted);margin:0.5rem 0">
                <span id="fileCount">{len(years)*19}</span> files · <span id="yearCount">{len(years)}</span> years × 19 variables
            </p>

            <div class="tabs" id="tabs">
                <button class="tab-btn active" onclick="showTab('bash')">Bash / curl</button>
                <button class="tab-btn" onclick="showTab('powershell')">PowerShell</button>
                <button class="tab-btn" onclick="showTab('python')">Python</button>
                <button class="tab-btn" onclick="showTab('urls')">URL list</button>
            </div>
            <div class="dl-box" id="dlBox" style="display:block"></div>

            <div class="range-actions">
                <button class="action-btn primary" onclick="downloadScript()">Download Script</button>
                <button class="action-btn" onclick="copyScript()">Copy to Clipboard</button>
                <button class="action-btn" onclick="downloadUrls()">Download URL List</button>
            </div>
        </div>

        <!-- Variables reference -->
        <div class="section">
            <h2>🌡️ Temperature Variables (bio01-bio11)</h2>
            <div class="var-grid">{var_cards(TEMP_VARS)}</div>
        </div>
        <div class="section">
            <h2>🌧️ Precipitation Variables (bio12-bio19)</h2>
            <div class="var-grid">{var_cards(PRECIP_VARS)}</div>
        </div>

        <!-- API -->
        <div class="section">
            <h2>📡 API</h2>
            <div style="font-family:monospace;font-size:0.85rem;line-height:2">
                <div><span style="color:var(--primary);font-weight:600">GET</span> <a href="/api/summary">/api/summary</a></div>
                <div><span style="color:var(--primary);font-weight:600">GET</span> <a href="/api/years">/api/years</a></div>
                <div><span style="color:var(--primary);font-weight:600">GET</span> <a href="/api/variables">/api/variables</a></div>
                <div><span style="color:var(--primary);font-weight:600">GET</span> /api/download/{{year}}/{{file}}</div>
                <div><span style="color:var(--primary);font-weight:600">GET</span> /api/scripts?start=1980&amp;end=2020&amp;fmt=bash</div>
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
    const yrMin = {yr_min}, yrMax = {yr_max};
    let currentTab = 'bash';

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
        loadScript();
    }}

    function showTab(fmt) {{
        currentTab = fmt;
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        event.target.classList.add('active');
        loadScript();
    }}

    function loadScript() {{
        const s = document.getElementById('rangeStart').value;
        const e = document.getElementById('rangeEnd').value;
        fetch(`/api/scripts?start=${{s}}&end=${{e}}&fmt=${{currentTab}}`)
            .then(r => r.text())
            .then(t => {{
                const box = document.getElementById('dlBox');
                box.textContent = t;
            }});
    }}

    function downloadScript() {{
        const s = document.getElementById('rangeStart').value;
        const e = document.getElementById('rangeEnd').value;
        const ext = currentTab === 'python' ? '.py' : currentTab === 'powershell' ? '.ps1' : '.sh';
        window.location.href = `/api/scripts?start=${{s}}&end=${{e}}&fmt=${{currentTab}}&download=bioclim_${{s}}-${{e}}${{ext}}`;
    }}

    function copyScript() {{
        const box = document.getElementById('dlBox');
        navigator.clipboard.writeText(box.textContent);
    }}

    function downloadUrls() {{
        const s = document.getElementById('rangeStart').value;
        const e = document.getElementById('rangeEnd').value;
        window.location.href = `/api/scripts?start=${{s}}&end=${{e}}&fmt=urls&download=bioclim_urls_${{s}}-${{e}}.txt`;
    }}

    // Init
    loadScript();
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
            <a href="/api/download/{year}/{fn}" class="dl-btn">Download</a>
        </div>"""

    return HTMLResponse(f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EcoSeek Bioclim — {year}</title>
    <link rel="icon" type="image/svg+xml" href="/static/favicon.svg">
    {CSS}
</head>
<body>
    <div class="hero" style="padding:2rem 1rem 1.5rem">
        <img src="/static/ecoseek-logo.svg" alt="EcoSeek" style="width:48px;height:48px">
        <h1>Year {year}</h1>
        <p>BIO01-BIO19 · ERA5-Land</p>
    </div>
    <div class="container">
        <a href="/" class="back-link">← All years</a>
        <div class="section">
            <h2>Files ({len(files)})</h2>
            {rows}
        </div>
    </div>
    <div class="footer">
        <a href="https://ecoseek.org">EcoSeek</a> ·
        <a href="https://cds.climate.copernicus.eu">ERA5-Land</a> ·
        <a href="https://github.com/alrobles/xclim">xclim</a> ·
        <a href="https://github.com/alrobles/ecoseek-bioclim">Source</a>
    </div>
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
        "source": "ERA5-Land",
        "spatial_resolution": "~0.1° (~9km)",
        "temporal_coverage": f"{min(data.keys())}-{max(data.keys())}" if data else "N/A",
        "variables": BIOCLIM_VARS,
        "years": inventory,
        "total_files": sum(len(f) for f in data.values()),
    }


@app.get("/api/download/{year}/{filename}")
def download_file(year: str, filename: str):
    filepath = DATA_DIR / year / filename
    if not filepath.exists() or not filepath.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(filepath, media_type="image/tiff", filename=filename)


@app.get("/api/scripts")
def generate_scripts(
    start: int = Query(1980),
    end: int = Query(2020),
    fmt: str = Query("bash"),
    download: str = Query(None),
):
    script = _dl_script(start, end, fmt)
    if download:
        return PlainTextResponse(
            script,
            headers={"Content-Disposition": f'attachment; filename="{download}"'},
        )
    return PlainTextResponse(script)


@app.get("/{year}/{filename}")
def direct_download(year: str, filename: str):
    filepath = DATA_DIR / year / filename
    if not filepath.exists() or not filepath.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    if not re.match(r"^bio\d{2}_\d{4}\.tif$", filename):
        raise HTTPException(status_code=400, detail="Invalid filename")
    return FileResponse(filepath, media_type="image/tiff", filename=filename)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
