"""
EcoSeek Bioclim — ERA5-Land bioclimatic variable server.

Serves BIO01-BIO19 GeoTIFF files derived from ERA5-Land (1980-2020)
as a browsable file server with API endpoints.

Endpoints:
  GET /                          File browser UI
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
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

# ── Config ──────────────────────────────────────────────────────────────────
DATA_DIR = Path(os.environ.get("BIOCLIM_DATA_DIR", "/data"))
PORT = int(os.environ.get("BIOCLIM_PORT", "8650"))

# Bioclim variable descriptions (WorldClim / CHELSA standard)
BIOCLIM_VARS = {
    "bio01": "Annual Mean Temperature",
    "bio02": "Mean Diurnal Range (Mean of monthly max-min temp)",
    "bio03": "Isothermality (bio02/bio07 * 100)",
    "bio04": "Temperature Seasonality (stddev * 100)",
    "bio05": "Max Temperature of Warmest Month",
    "bio06": "Min Temperature of Coldest Month",
    "bio07": "Temperature Annual Range (bio05-bio06)",
    "bio08": "Mean Temperature of Wettest Quarter",
    "bio09": "Mean Temperature of Driest Quarter",
    "bio10": "Mean Temperature of Warmest Quarter",
    "bio11": "Mean Temperature of Coldest Quarter",
    "bio12": "Annual Precipitation",
    "bio13": "Precipitation of Wettest Month",
    "bio14": "Precipitation of Driest Month",
    "bio15": "Precipitation Seasonality (Coefficient of Variation)",
    "bio16": "Precipitation of Wettest Quarter",
    "bio17": "Precipitation of Driest Quarter",
    "bio18": "Precipitation of Warmest Quarter",
    "bio19": "Precipitation of Coldest Quarter",
}

app = FastAPI(
    title="EcoSeek Bioclim",
    version="1.0.0",
    description="ERA5-Land bioclimatic variables (BIO01-BIO19, 1980-2020)",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Helpers ─────────────────────────────────────────────────────────────────
def _scan_years() -> Dict[str, List[str]]:
    """Scan data dir and return {year: [filenames]}."""
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


# ── API Endpoints ───────────────────────────────────────────────────────────
@app.get("/api/years")
def list_years():
    """List all available years."""
    data = _scan_years()
    return {"years": sorted(data.keys()), "count": len(data)}


@app.get("/api/variables")
def list_variables():
    """List bioclimatic variable definitions."""
    return {"variables": BIOCLIM_VARS}


@app.get("/api/summary")
def summary():
    """Full inventory: years × variables."""
    data = _scan_years()
    inventory = {}
    for year, files in data.items():
        vars_in_year = sorted(set(
            f.split("_")[0] for f in files if f.endswith(".tif")
        ))
        inventory[year] = {
            "count": len(files),
            "variables": vars_in_year,
        }
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
    """Download a specific bioclim file."""
    filepath = DATA_DIR / year / filename
    if not filepath.exists() or not filepath.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(
        filepath,
        media_type="image/tiff",
        filename=filename,
    )


# ── File browser routes ────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
def index():
    """Main file browser page."""
    data = _scan_years()
    years_html = ""
    for year in sorted(data.keys(), reverse=True):
        files = data[year]
        vars_in_year = sorted(set(f.split("_")[0] for f in files))
        total_size = sum((DATA_DIR / year / f).stat().st_size for f in files)
        size_str = _file_size_human(Path("/dev/null"))  # placeholder
        years_html += f"""
        <tr>
            <td><a href="/{year}/" class="year-link">{year}</a></td>
            <td>{len(files)} files</td>
            <td>{', '.join(vars_in_year)}</td>
            <td><a href="/{year}/" class="browse-btn">Browse</a></td>
        </tr>"""

    return HTMLResponse(f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EcoSeek Bioclim — ERA5-Land Bioclimatic Variables</title>
    <style>
        :root {{
            --primary: #2563eb;
            --primary-light: #dbeafe;
            --primary-dark: #1d4ed8;
            --bg: #f8fafc;
            --card: #ffffff;
            --text: #0f172a;
            --text-secondary: #64748b;
            --border: #e2e8f0;
            --success: #10b981;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.6;
        }}
        .header {{
            background: linear-gradient(135deg, var(--primary), var(--primary-dark));
            color: white;
            padding: 2rem;
            text-align: center;
        }}
        .header h1 {{
            font-size: 2rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
        }}
        .header p {{
            opacity: 0.9;
            font-size: 1.1rem;
        }}
        .container {{
            max-width: 1100px;
            margin: 2rem auto;
            padding: 0 1rem;
        }}
        .info-cards {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }}
        .info-card {{
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1.5rem;
            text-align: center;
        }}
        .info-card .number {{
            font-size: 2rem;
            font-weight: 700;
            color: var(--primary);
        }}
        .info-card .label {{
            color: var(--text-secondary);
            font-size: 0.9rem;
        }}
        table {{
            width: 100%;
            background: var(--card);
            border-radius: 12px;
            overflow: hidden;
            border: 1px solid var(--border);
            border-collapse: collapse;
        }}
        th {{
            background: var(--primary);
            color: white;
            padding: 1rem;
            text-align: left;
            font-weight: 600;
        }}
        td {{
            padding: 0.8rem 1rem;
            border-bottom: 1px solid var(--border);
        }}
        tr:last-child td {{ border-bottom: none; }}
        tr:hover td {{ background: var(--primary-light); }}
        .year-link {{
            color: var(--primary);
            text-decoration: none;
            font-weight: 600;
            font-size: 1.1rem;
        }}
        .year-link:hover {{ text-decoration: underline; }}
        .browse-btn {{
            background: var(--primary);
            color: white;
            padding: 0.4rem 1rem;
            border-radius: 6px;
            text-decoration: none;
            font-size: 0.85rem;
            font-weight: 500;
        }}
        .browse-btn:hover {{ background: var(--primary-dark); }}
        .api-section {{
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1.5rem;
            margin-top: 2rem;
        }}
        .api-section h2 {{
            color: var(--primary);
            margin-bottom: 1rem;
        }}
        .api-endpoint {{
            font-family: 'SF Mono', Monaco, 'Cascadia Code', monospace;
            background: #1e293b;
            color: #e2e8f0;
            padding: 0.8rem 1rem;
            border-radius: 8px;
            margin: 0.5rem 0;
            font-size: 0.9rem;
            overflow-x: auto;
        }}
        .api-endpoint a {{
            color: #7dd3fc;
            text-decoration: none;
        }}
        .footer {{
            text-align: center;
            color: var(--text-secondary);
            padding: 2rem;
            font-size: 0.85rem;
        }}
        .footer a {{ color: var(--primary); text-decoration: none; }}
        .var-table {{ margin-top: 2rem; }}
        .var-table th {{ background: var(--success); }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🌍 EcoSeek Bioclim</h1>
        <p>ERA5-Land Bioclimatic Variables (BIO01-BIO19) · 1980-2020</p>
    </div>

    <div class="container">
        <div class="info-cards">
            <div class="info-card">
                <div class="number">41</div>
                <div class="label">Years (1980-2020)</div>
            </div>
            <div class="info-card">
                <div class="number">19</div>
                <div class="label">Bioclim Variables</div>
            </div>
            <div class="info-card">
                <div class="number">779</div>
                <div class="label">GeoTIFF Files</div>
            </div>
            <div class="info-card">
                <div class="number">~9km</div>
                <div class="label">Spatial Resolution</div>
            </div>
        </div>

        <table>
            <thead>
                <tr>
                    <th>Year</th>
                    <th>Files</th>
                    <th>Variables</th>
                    <th>Action</th>
                </tr>
            </thead>
            <tbody>
                {years_html}
            </tbody>
        </table>

        <div class="api-section">
            <h2>📡 API Access</h2>
            <p style="color: var(--text-secondary); margin-bottom: 1rem;">
                Programmatic access for R, Python, and ecoSeek pipelines:
            </p>
            <div class="api-endpoint"><a href="/api/summary">GET /api/summary</a> — Full inventory (years × variables)</div>
            <div class="api-endpoint"><a href="/api/years">GET /api/years</a> — List available years</div>
            <div class="api-endpoint"><a href="/api/variables">GET /api/variables</a> — Variable definitions</div>
            <div class="api-endpoint">GET /api/download/{{year}}/{{filename}} — Download file</div>
        </div>

        <div class="var-table">
            <table>
                <thead>
                    <tr><th>Variable</th><th>Description</th></tr>
                </thead>
                <tbody>
                    {''.join(f'<tr><td><strong>{k}</strong></td><td>{v}</td></tr>' for k, v in BIOCLIM_VARS.items())}
                </tbody>
            </table>
        </div>
    </div>

    <div class="footer">
        Powered by <a href="https://ecoseek.org">EcoSeek</a> ·
        Data: <a href="https://cds.climate.copernicus.eu">ERA5-Land (Copernicus CDS)</a> ·
        Processed with xclim
    </div>
</body>
</html>""")


@app.get("/{year}/", response_class=HTMLResponse)
def year_browser(year: str):
    """Browse files for a specific year."""
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
        filepath = year_dir / fn
        size = _file_size_human(filepath)
        rows += f"""
        <tr>
            <td><a href="/{year}/{fn}" class="file-link">{fn}</a></td>
            <td>{desc}</td>
            <td>{size}</td>
            <td><a href="/api/download/{year}/{fn}" class="browse-btn">Download</a></td>
        </tr>"""

    return HTMLResponse(f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EcoSeek Bioclim — {year}</title>
    <style>
        :root {{
            --primary: #2563eb; --primary-light: #dbeafe; --primary-dark: #1d4ed8;
            --bg: #f8fafc; --card: #ffffff; --text: #0f172a;
            --text-secondary: #64748b; --border: #e2e8f0;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg); color: var(--text); line-height: 1.6;
        }}
        .header {{
            background: linear-gradient(135deg, var(--primary), var(--primary-dark));
            color: white; padding: 1.5rem 2rem;
        }}
        .header h1 {{ font-size: 1.5rem; }}
        .header a {{ color: rgba(255,255,255,0.8); text-decoration: none; font-size: 0.9rem; }}
        .header a:hover {{ color: white; }}
        .container {{ max-width: 1000px; margin: 2rem auto; padding: 0 1rem; }}
        table {{
            width: 100%; background: var(--card); border-radius: 12px;
            overflow: hidden; border: 1px solid var(--border); border-collapse: collapse;
        }}
        th {{
            background: var(--primary); color: white; padding: 1rem;
            text-align: left; font-weight: 600;
        }}
        td {{ padding: 0.8rem 1rem; border-bottom: 1px solid var(--border); }}
        tr:last-child td {{ border-bottom: none; }}
        tr:hover td {{ background: var(--primary-light); }}
        .file-link {{
            color: var(--primary); text-decoration: none;
            font-family: 'SF Mono', Monaco, monospace; font-weight: 500;
        }}
        .file-link:hover {{ text-decoration: underline; }}
        .browse-btn {{
            background: var(--primary); color: white; padding: 0.3rem 0.8rem;
            border-radius: 6px; text-decoration: none; font-size: 0.85rem;
        }}
        .browse-btn:hover {{ background: var(--primary-dark); }}
        .back {{ margin-bottom: 1rem; }}
        .back a {{ color: var(--primary); text-decoration: none; }}
    </style>
</head>
<body>
    <div class="header">
        <a href="/">← Back to all years</a>
        <h1>🌍 EcoSeek Bioclim — Year {year}</h1>
    </div>
    <div class="container">
        <table>
            <thead>
                <tr><th>File</th><th>Variable</th><th>Size</th><th>Action</th></tr>
            </thead>
            <tbody>{rows}</tbody>
        </table>
    </div>
</body>
</html>""")


@app.get("/{year}/{filename}")
def direct_download(year: str, filename: str):
    """Direct file download by year/filename path."""
    filepath = DATA_DIR / year / filename
    if not filepath.exists() or not filepath.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    if not re.match(r"^bio\d{2}_\d{4}\.tif$", filename):
        raise HTTPException(status_code=400, detail="Invalid filename pattern")
    return FileResponse(filepath, media_type="image/tiff", filename=filename)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
