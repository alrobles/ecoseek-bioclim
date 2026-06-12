# 🌍 EcoSeek Bioclim

ERA5-Land bioclimatic variables (BIO01-BIO19) served as a modern file server with REST API.

**Live:** [bioclim.ecoseek.org](https://bioclim.ecoseek.org)

## Features (v2.0)

- 🌓 Dark mode (auto-detect + toggle, persisted)
- 📥 Quick download by year
- 📦 Batch download with curl one-liner
- 📡 REST API for programmatic access
- 🎨 Modern UI (Inter + JetBrains Mono, neumorphic cards)
- 📱 Responsive mobile-first design
- 🔗 Integrated with [EcoSeek](https://ecoseek.org) ecosystem

## Data

| Property | Value |
|---|---|
| Source | ERA5-Land (Copernicus Climate Data Store) |
| Variables | 19 WorldClim-standard bioclimatic indices (bio01-bio19) |
| Temporal coverage | 1980-2020 (41 years) |
| Spatial resolution | ~0.1° (~9km), global |
| Format | GeoTIFF (compressed, tiled) |
| Processing | [xclim](https://github.com/alrobles/xclim) (Python) via Slurm on KU HPC |
| Total | 779 files, ~5.6 GB |

## Quick Start

```bash
# Docker
docker compose up -d
# Open http://localhost:8650

# Download all data (one-liner)
curl -sSf "https://bioclim.ecoseek.org/api/scripts?start=1980&end=2020&fmt=bash" -o bioclim.sh && bash bioclim.sh

# Download specific year range
curl -sSf "https://bioclim.ecoseek.org/api/scripts?start=2010&end=2020&fmt=bash" -o bioclim.sh && bash bioclim.sh
```

## API

| Endpoint | Description |
|---|---|
| `GET /` | Landing page with file browser |
| `GET /api/years` | List available years |
| `GET /api/variables` | Bioclimatic variable definitions |
| `GET /api/summary` | Full inventory (years × variables) |
| `GET /api/download/{year}/{file}` | Download a specific GeoTIFF |
| `GET /api/scripts?start=X&end=Y&fmt=bash` | Generate download script |
| `GET /api/scripts?start=X&end=Y&fmt=urls` | Generate URL list |
| `GET /{year}/` | Browse files for a year |
| `GET /{year}/{filename}` | Direct file download |

### Script formats

```
fmt=bash      → Shell script with curl commands
fmt=urls      → Plain text URL list (one per line)
```

## Python Client

```python
from ecoseek_bioclim import BioclimClient

client = BioclimClient()

# List years
years = client.years()  # ['1980', ..., '2020']

# Get summary
summary = client.summary()
print(summary["total_files"])  # 779

# Download a file
client.download("bio01", 2020, "/tmp/bio01_2020.tif")

# Load as rasterio
with client.open_rasterio("bio01", 2020) as src:
    data = src.read(1)

# Download all
client.download_all("./data", years=[2018, 2019, 2020])
```

## R Client

```r
library(terra)

url <- "https://bioclim.ecoseek.org/api/download/2020/bio01_2020.tif"
dest <- tempfile(fileext = ".tif")
download.file(url, dest, mode = "wb")
r <- rast(dest)
plot(r, main = "Annual Mean Temperature (2020)")
```

## EcoSeek Integration

| Service | URL | Description |
|---|---|---|
| EcoSeek | [ecoseek.org](https://ecoseek.org) | Main frontend |
| Emily | [emily.ecoseek.org](https://emily.ecoseek.org) | AI assistant API |
| **Bioclim** | [bioclim.ecoseek.org](https://bioclim.ecoseek.org) | This service |
| Kids | [kids.ecoseek.org](https://kids.ecoseek.org) | Kid-friendly version |
| Hermes | [hermes.ecoseek.org](https://hermes.ecoseek.org) | Agent gateway |
| Monitor | [monitor.ecoseek.org](https://monitor.ecoseek.org) | System monitoring |

## Architecture

```
bioclim.ecoseek.org
       │
       ▼
  Cloudflare Tunnel (/etc/cloudflared/config.yml)
       │
       ▼
  FastAPI (Docker, port 8650)
       │
       ▼
  /media/reumanlab/TOSHIBA_EXT/era5-bioclim/  (read-only, no duplication)
       │
       ├── 1980/  (19 TIFs)
       ├── 1981/  (19 TIFs)
       ├── ...
       └── 2020/  (19 TIFs)
```

## Deployment

```bash
# Build and run
cd /home/reumanlab/dev/ecoseek-bioclim
docker build -t ecoseek-bioclim .
docker rm -f ecoseek-bioclim
docker run -d --name ecoseek-bioclim \
  -p 127.0.0.1:8650:8650 \
  -v /media/reumanlab/TOSHIBA_EXT/era5-bioclim:/data:ro \
  --restart unless-stopped \
  ecoseek-bioclim

# Verify
curl -s https://bioclim.ecoseek.org/api/years

# CF Tunnel route (in /etc/cloudflared/config.yml)
# - hostname: bioclim.ecoseek.org
#   service: http://127.0.0.1:8650
```

## Pipeline (KU HPC)

The data was generated using a 3-phase pipeline:

1. **Download** — ERA5-Land hourly data via CDS API (`download_month.R`)
2. **Monthly** — Aggregate hourly → monthly means/sums (`phase1b_monthly.R`)
3. **Bioclim** — Compute BIO01-BIO19 using xclim (`phase2_bioclim.R`)

Scripts: `~/scratch/era5-land/scripts/` on KU HPC cluster.

## Versioning

| Tag | Description | Rollback |
|---|---|---|
| `v1.0-stable` | Initial release (basic HTML, no dark mode) | `git checkout v1.0-stable` |
| `v2.0` | Current (dark mode, Inter font, terminal style, nav) | `git checkout v2.0` |
| `master` | Latest | `git checkout master` |

## Bioclimatic Variables

| Var | Description | Type |
|---|---|---|
| bio01 | Annual Mean Temperature | 🌡️ Temp |
| bio02 | Mean Diurnal Range | 🌡️ Temp |
| bio03 | Isothermality | 🌡️ Temp |
| bio04 | Temperature Seasonality | 🌡️ Temp |
| bio05 | Max Temp Warmest Month | 🌡️ Temp |
| bio06 | Min Temp Coldest Month | 🌡️ Temp |
| bio07 | Temperature Annual Range | 🌡️ Temp |
| bio08 | Mean Temp Wettest Quarter | 🌡️ Temp |
| bio09 | Mean Temp Driest Quarter | 🌡️ Temp |
| bio10 | Mean Temp Warmest Quarter | 🌡️ Temp |
| bio11 | Mean Temp Coldest Quarter | 🌡️ Temp |
| bio12 | Annual Precipitation | 🌧️ Precip |
| bio13 | Precip Wettest Month | 🌧️ Precip |
| bio14 | Precip Driest Month | 🌧️ Precip |
| bio15 | Precip Seasonality (CV) | 🌧️ Precip |
| bio16 | Precip Wettest Quarter | 🌧️ Precip |
| bio17 | Precip Driest Quarter | 🌧️ Precip |
| bio18 | Precip Warmest Quarter | 🌧️ Precip |
| bio19 | Precip Coldest Quarter | 🌧️ Precip |

## License

- Data: [ERA5-Land](https://cds.climate.copernicus.eu) (Copernicus License)
- Processing: [xclim](https://github.com/alrobles/xclim)
- Code: MIT
- Part of [EcoSeek](https://ecoseek.org) by [alrobles](https://github.com/alrobles)
