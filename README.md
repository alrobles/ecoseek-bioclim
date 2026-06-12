# 🌍 EcoSeek Bioclim

ERA5-Land bioclimatic variables (BIO01-BIO19) served as a browsable file server.

**Live:** [bioclim.ecoseek.org](https://bioclim.ecoseek.org)

## Data

- **Source:** ERA5-Land (Copernicus Climate Data Store)
- **Variables:** 19 WorldClim-standard bioclimatic indices (bio01-bio19)
- **Temporal coverage:** 1980-2020 (41 years)
- **Spatial resolution:** ~0.1° (~9km), global
- **Format:** GeoTIFF (compressed, tiled)
- **Processing:** xclim (Python) via Slurm on KU HPC cluster
- **Total:** 779 files, ~5.6 GB

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

## Quick Start

```bash
docker compose up -d
# Open http://localhost:8650
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

## Python Client

```python
import requests
import rasterio

# Get summary
resp = requests.get("https://bioclim.ecoseek.org/api/summary").json()
print(f"Years: {resp['temporal_coverage']}, Files: {resp['total_files']}")

# Download a file
url = "https://bioclim.ecoseek.org/api/download/2020/bio01_2020.tif"
r = rasterio.open(url)
```

## Integration with EcoSeek

This service is part of the [EcoSeek](https://ecoseek.org) ecosystem:

- **ecoseek.org** — Main frontend (Emily AI assistant)
- **emily.ecoseek.org** — Emily API server
- **bioclim.ecoseek.org** — This service (bioclimatic data)
- **kids.ecoseek.org** — EcoSeek Kids

## Pipeline

The data was generated using a 3-phase pipeline on the KU HPC cluster:

1. **Download** — ERA5-Land hourly data via CDS API (t2m + tp)
2. **Monthly** — Aggregate to monthly means/sums (tas, tasmax, tasmin, pr)
3. **Bioclim** — Compute BIO01-BIO19 using xclim

Pipeline scripts: `~/scratch/era5-land/scripts/` on KU HPC.

## License

Data: [ERA5-Land](https://cds.climate.copernicus.eu) (Copernicus License)
Code: MIT
