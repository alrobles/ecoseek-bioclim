# 🌍 EcoSeek Bioclim

ERA5-Land bioclimatic variables (BIO01-BIO19) served as a browsable file server with REST API.

**Live:** [bioclim.ecoseek.org](https://bioclim.ecoseek.org)

## Data

| Property | Value |
|---|---|
| Source | ERA5-Land (Copernicus Climate Data Store) |
| Variables | 19 WorldClim-standard bioclimatic indices (bio01-bio19) |
| Temporal coverage | 1980-2020 (41 years) |
| Spatial resolution | ~0.1° (~9km), global |
| Format | GeoTIFF (compressed, tiled) |
| Processing | [xclim](https://github.com/alrobles/xclim) (Python) via Slurm on KU HPC cluster |
| Total | 779 files, ~5.6 GB |

## Quick Start

```bash
docker compose up -d
# Open http://localhost:8650
```

## API Endpoints

| Endpoint | Description |
|---|---|
| `GET /` | File browser UI |
| `GET /api/years` | List available years |
| `GET /api/variables` | Bioclimatic variable definitions |
| `GET /api/summary` | Full inventory (years × variables) |
| `GET /api/download/{year}/{file}` | Download a specific file |
| `GET /{year}/` | Browse files for a year |
| `GET /{year}/{filename}` | Direct download |

## Python Client

```python
from ecoseek_bioclim import BioclimClient

client = BioclimClient()

# List years
years = client.years()  # ['1980', '1981', ..., '2020']

# Get summary
summary = client.summary()
print(summary["total_files"])  # 779

# Download a file
client.download("bio01", 2020, "/tmp/bio01_2020.tif")

# Load as rasterio dataset
with client.open_rasterio("bio01", 2020) as src:
    print(src.shape)
    data = src.read(1)

# Load as xarray
da = client.open_xarray("bio01", 2020)
```

## R Client

```r
library(terra)

# Download and load a bioclimatic variable
url <- "https://bioclim.ecoseek.org/api/download/2020/bio01_2020.tif"
dest <- tempfile(fileext = ".tif")
download.file(url, dest, mode = "wb")
r <- rast(dest)
plot(r, main = "Annual Mean Temperature (2020)")
```

## Integration with EcoSeek

This service is part of the [EcoSeek](https://ecoseek.org) ecosystem:

| Service | URL | Description |
|---|---|---|
| EcoSeek | [ecoseek.org](https://ecoseek.org) | Main frontend (Emily AI assistant) |
| Emily | [emily.ecoseek.org](https://emily.ecoseek.org) | Emily API server |
| **Bioclim** | [bioclim.ecoseek.org](https://bioclim.ecoseek.org) | This service (bioclimatic data) |
| Kids | [kids.ecoseek.org](https://kids.ecoseek.org) | EcoSeek Kids |
| Hermes | [hermes.ecoseek.org](https://hermes.ecoseek.org) | Hermes Agent gateway |
| Monitor | [monitor.ecoseek.org](https://monitor.ecoseek.org) | System monitoring |

## Bioclimatic Variables

| Variable | Description |
|---|---|
| bio01 | Annual Mean Temperature |
| bio02 | Mean Diurnal Range |
| bio03 | Isothermality |
| bio04 | Temperature Seasonality |
| bio05 | Max Temperature of Warmest Month |
| bio06 | Min Temperature of Coldest Month |
| bio07 | Temperature Annual Range |
| bio08 | Mean Temperature of Wettest Quarter |
| bio09 | Mean Temperature of Driest Quarter |
| bio10 | Mean Temperature of Warmest Quarter |
| bio11 | Mean Temperature of Coldest Quarter |
| bio12 | Annual Precipitation |
| bio13 | Precipitation of Wettest Month |
| bio14 | Precipitation of Driest Month |
| bio15 | Precipitation Seasonality |
| bio16 | Precipitation of Wettest Quarter |
| bio17 | Precipitation of Driest Quarter |
| bio18 | Precipitation of Warmest Quarter |
| bio19 | Precipitation of Coldest Quarter |

## Pipeline

The data was generated using a 3-phase pipeline on the KU HPC cluster:

1. **Download** — ERA5-Land hourly data via CDS API (t2m + tp)
2. **Monthly** — Aggregate to monthly means/sums (tas, tasmax, tasmin, pr)
3. **Bioclim** — Compute BIO01-BIO19 using [xclim](https://github.com/alrobles/xclim)

Pipeline scripts: `~/scratch/era5-land/scripts/` on KU HPC.

## Architecture

```
bioclim.ecoseek.org
       │
       ▼
  Cloudflare Tunnel
       │
       ▼
  FastAPI (port 8650)
       │
       ▼
  /media/toshiba/era5-bioclim/  (read-only mount)
       │
       ├── 1980/
       │   ├── bio01_1980.tif
       │   ├── ...
       │   └── bio19_1980.tif
       ├── ...
       └── 2020/
           ├── bio01_2020.tif
           ├── ...
           └── bio19_2020.tif
```

## License

- Data: [ERA5-Land](https://cds.climate.copernicus.eu) (Copernicus License)
- Processing: [xclim](https://github.com/alrobles/xclim)
- Code: MIT
- Part of [EcoSeek](https://ecoseek.org) by [alrobles](https://github.com/alrobles)
