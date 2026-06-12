"""
EcoSeek Bioclim — ERA5-Land bioclimatic variable server.

Serves BIO01-BIO19 GeoTIFF files derived from ERA5-Land (1980-2020)
as a browsable file server with API endpoints.

Endpoints:
  GET /                          Landing page + download grid
  GET /api/years                 List available years
  GET /api/variables             List bioclimatic variables (bio01-bio19)
  GET /api/summary               Full inventory (years x variables)
  GET /api/download/{year}/{fn}  Download a specific file
  GET /{year}/                   Browse files for a year
  GET /{year}/{filename}         Direct download
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Dict, List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

# ── Config ──────────────────────────────────────────────────────────────────
DATA_DIR = Path(os.environ.get("BIOCLIM_DATA_DIR", "/data"))
PORT = int(os.environ.get("BIOCLIM_PORT", "8650"))

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).parent.parent / "frontend" / "public"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ── Helpers ─────────────────────────────────────────────────────────────────
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


# ── Shared CSS ──────────────────────────────────────────────────────────────
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

    /* Hero */
    .hero {
        text-align: center; padding: 3rem 1rem 2rem;
        border-bottom: 1px solid var(--border);
    }
    .hero img { width: 64px; height: 64px; margin-bottom: 1rem; }
    .hero h1 { font-size: 1.8rem; font-weight: 700; margin-bottom: 0.3rem; }
    .hero p { color: var(--text-muted); font-size: 1rem; }

    /* Stats */
    .stats {
        display: flex; justify-content: center; gap: 2rem;
        padding: 1.5rem 1rem; flex-wrap: wrap;
    }
    .stat { text-align: center; }
    .stat .num { font-size: 1.5rem; font-weight: 700; color: var(--primary); }
    .stat .lbl { font-size: 0.8rem; color: var(--text-muted); }

    /* Container */
    .container { max-width: 800px; margin: 0 auto; padding: 0 1rem; }

    /* Year selector */
    .year-grid {
        display: flex; flex-wrap: wrap; gap: 0.5rem;
        justify-content: center; padding: 1rem 0 2rem;
    }
    .year-btn {
        display: inline-block; padding: 0.5rem 1rem;
        background: var(--card); border: 1px solid var(--border);
        border-radius: 8px; font-size: 0.9rem; font-weight: 500;
        color: var(--text); cursor: pointer; transition: all 0.15s;
    }
    .year-btn:hover {
        background: var(--primary); color: white; border-color: var(--primary);
        text-decoration: none;
    }

    /* Variable grid */
    .section-title {
        font-size: 1.1rem; font-weight: 600; padding: 1.5rem 0 0.5rem;
        border-bottom: 2px solid var(--primary); display: inline-block;
        margin-bottom: 1rem;
    }
    .var-grid {
        display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
        gap: 0.6rem; margin-bottom: 2rem;
    }
    .var-card {
        display: flex; align-items: center; gap: 0.6rem;
        padding: 0.6rem 0.8rem; background: var(--primary-light);
        border-radius: 8px; font-size: 0.85rem;
    }
    .var-code {
        font-weight: 700; color: var(--primary); font-family: monospace;
        min-width: 3.5rem;
    }

    /* API section */
    .api-section {
        background: #f8fafc; border: 1px solid var(--border);
        border-radius: 12px; padding: 1.5rem; margin: 2rem 0;
    }
    .api-section h2 { color: var(--primary); font-size: 1rem; margin-bottom: 0.8rem; }
    .api-row {
        font-family: 'SF Mono', Monaco, monospace; font-size: 0.85rem;
        padding: 0.4rem 0; color: #334155;
    }
    .api-method { color: var(--primary); font-weight: 600; }

    /* Footer */
    .footer {
        text-align: center; color: var(--text-muted); font-size: 0.8rem;
        padding: 2rem 1rem; border-top: 1px solid var(--border); margin-top: 2rem;
    }

    /* File list */
    .file-list { margin: 1rem 0 2rem; }
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
        border-radius: 6px; font-size: 0.8rem; font-weight: 500;
        margin-left: 1rem;
    }
    .dl-btn:hover { background: var(--primary-dark); text-decoration: none; }

    .back-link {
        display: inline-block; padding: 0.8rem 0; color: var(--primary);
        font-size: 0.9rem;
    }
</style>
"""


# ── Landing page ────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
def index():
    data = _scan_years()
    years = sorted(data.keys())
    year_range = f"{years[0]}–{years[-1]}" if years else "N/A"
    total = sum(len(f) for f in data.values())

    year_btns = "".join(
        f'<a href="/{y}/" class="year-btn">{y}</a>'
        for y in sorted(years, reverse=True)
    )

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
        <p>ERA5-Land bioclimatic variables · BIO01-BIO19 · {year_range}</p>
    </div>

    <div class="stats">
        <div class="stat"><div class="num">{len(years)}</div><div class="lbl">Years</div></div>
        <div class="stat"><div class="num">19</div><div class="lbl">Variables</div></div>
        <div class="stat"><div class="num">{total}</div><div class="lbl">GeoTIFFs</div></div>
        <div class="stat"><div class="num">~9km</div><div class="lbl">Resolution</div></div>
    </div>

    <div class="container">
        <div class="section-title">Download by Year</div>
        <div class="year-grid">{year_btns}</div>

        <div class="section-title">Temperature Variables</div>
        <div class="var-grid">{var_cards(TEMP_VARS)}</div>

        <div class="section-title">Precipitation Variables</div>
        <div class="var-grid">{var_cards(PRECIP_VARS)}</div>

        <div class="api-section">
            <h2>📡 API</h2>
            <div class="api-row"><span class="api-method">GET</span> <a href="/api/summary">/api/summary</a> — Full inventory</div>
            <div class="api-row"><span class="api-method">GET</span> <a href="/api/years">/api/years</a> — Available years</div>
            <div class="api-row"><span class="api-method">GET</span> <a href="/api/variables">/api/variables</a> — Variable definitions</div>
            <div class="api-row"><span class="api-method">GET</span> /api/download/{{year}}/{{file}} — Download</div>
        </div>
    </div>

    <div class="footer">
        <a href="https://ecoseek.org">EcoSeek</a> ·
        Data: <a href="https://cds.climate.copernicus.eu">ERA5-Land (Copernicus CDS)</a> ·
        Processed with <a href="https://github.com/alrobles/xclim">xclim</a> ·
        <a href="https://github.com/alrobles/ecoseek-bioclim">Source</a>
    </div>
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
        raise HTTPException(status_code=404, detail="No files for this year")

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
    <div class="hero" style="padding: 2rem 1rem 1.5rem;">
        <img src="/static/ecoseek-logo.svg" alt="EcoSeek" style="width:48px;height:48px;">
        <h1>Year {year}</h1>
        <p>BIO01-BIO19 · ERA5-Land</p>
    </div>
    <div class="container">
        <a href="/" class="back-link">← All years</a>
        <div class="file-list">{rows}</div>
    </div>
    <div class="footer">
        <a href="https://ecoseek.org">EcoSeek</a> ·
        Data: <a href="https://cds.climate.copernicus.eu">ERA5-Land (Copernicus CDS)</a> ·
        Processed with <a href="https://github.com/alrobles/xclim">xclim</a> ·
        <a href="https://github.com/alrobles/ecoseek-bioclim">Source</a>
    </div>
</body>
</html>""")


# ── API Endpoints ───────────────────────────────────────────────────────────
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
