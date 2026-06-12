"""
ecoseek_bioclim — Python client for EcoSeek Bioclim API.

Usage:
    from ecoseek_bioclim import BioclimClient

    client = BioclimClient("https://bioclim.ecoseek.org")
    
    # List years
    years = client.years()  # ['1980', '1981', ..., '2020']
    
    # Get summary
    summary = client.summary()
    print(summary["total_files"])  # 779
    
    # Download a file
    client.download("bio01", 2020, "/tmp/bio01_2020.tif")
    
    # Load as rasterio dataset (requires rasterio)
    with client.open_rasterio("bio01", 2020) as src:
        print(src.shape)

    # Load as xarray (requires rioxarray)
    ds = client.open_xarray("bio01", 2020)
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urljoin

import requests


class BioclimClient:
    """Client for the EcoSeek Bioclim API."""

    def __init__(self, base_url: str = "https://bioclim.ecoseek.org", timeout: int = 60):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()

    def _get(self, path: str) -> dict:
        resp = self.session.get(f"{self.base_url}{path}", timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def years(self) -> List[str]:
        """List available years."""
        return self._get("/api/years")["years"]

    def variables(self) -> Dict[str, str]:
        """Get bioclimatic variable definitions."""
        return self._get("/api/variables")["variables"]

    def summary(self) -> dict:
        """Get full inventory summary."""
        return self._get("/api/summary")

    def download_url(self, variable: str, year: int) -> str:
        """Get download URL for a bioclim file."""
        return f"{self.base_url}/api/download/{year}/{variable}_{year}.tif"

    def download(self, variable: str, year: int, dest: str | Path) -> Path:
        """Download a bioclim file to disk.

        Args:
            variable: Bioclim variable code (e.g., "bio01")
            year: Year (e.g., 2020)
            dest: Destination path or directory

        Returns:
            Path to downloaded file
        """
        dest = Path(dest)
        filename = f"{variable}_{year}.tif"
        if dest.is_dir():
            dest = dest / filename

        url = self.download_url(variable, year)
        resp = self.session.get(url, timeout=self.timeout, stream=True)
        resp.raise_for_status()

        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(dest, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)

        return dest

    def open_rasterio(self, variable: str, year: int):
        """Open a bioclim file as a rasterio dataset (requires rasterio).

        Usage:
            with client.open_rasterio("bio01", 2020) as src:
                data = src.read(1)
        """
        import rasterio
        url = self.download_url(variable, year)
        return rasterio.open(url)

    def open_xarray(self, variable: str, year: int):
        """Open a bioclim file as an xarray DataArray (requires rioxarray).

        Usage:
            da = client.open_xarray("bio01", 2020)
        """
        import rioxarray
        import xarray as xr
        url = self.download_url(variable, year)
        return xr.open_dataarray(url, engine="rasterio")

    def download_all(self, dest: str | Path, variables: Optional[List[str]] = None,
                     years: Optional[List[int]] = None) -> List[Path]:
        """Download multiple bioclim files.

        Args:
            dest: Destination directory
            variables: List of variables (default: all 19)
            years: List of years (default: all available)

        Returns:
            List of downloaded file paths
        """
        dest = Path(dest)
        if variables is None:
            variables = sorted(self.variables().keys())
        if years is None:
            years = [int(y) for y in self.years()]

        downloaded = []
        for year in years:
            for var in variables:
                path = self.download(var, year, dest / str(year))
                downloaded.append(path)

        return downloaded


# Convenience functions
_default_client = None

def _get_client() -> BioclimClient:
    global _default_client
    if _default_client is None:
        _default_client = BioclimClient()
    return _default_client

def years() -> List[str]:
    return _get_client().years()

def variables() -> Dict[str, str]:
    return _get_client().variables()

def download(variable: str, year: int, dest: str | Path) -> Path:
    return _get_client().download(variable, year, dest)
