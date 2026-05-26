"""itrdb.py — International Tree-Ring Data Bank (ITRDB) API client.

exports: search_itrdb, fetch_itrdb_series
used_by: dendro.ui.itrdb_dialog
rules:
  - Network requests must be non-blocking in UI or run in threads.
  - Handle malformed JSON or missing fields gracefully.
"""

from __future__ import annotations

import json
import logging
import urllib.request
import urllib.parse
from dataclasses import dataclass
from typing import Any

from dendro.models.series import RingWidthSeries
from dendro.io.tucson import read_tucson

logger = logging.getLogger(__name__)

# Base API endpoint for NOAA ITRDB
SEARCH_API_URL = "https://www.ncei.noaa.gov/access/paleo-search/study/search.json"

@dataclass
class ITRDBStudy:
    """Represents a dataset returned from the ITRDB API."""
    study_id: str
    study_name: str
    investigators: str
    site_name: str
    species: str
    earliest_year: int | str
    most_recent_year: int | str
    rwl_url: str | None

def search_itrdb(keyword: str, limit: int = 50) -> list[ITRDBStudy]:
    """Search the ITRDB via NOAA API for tree ring data.
    
    Args:
        keyword: Search term (e.g., 'oak', 'colorado', 'douglas fir')
        limit: Max results to return
        
    Returns:
        A list of parsed ITRDBStudy objects.
    """
    params = {
        "dataPublisher": "NOAA",
        "dataTypeId": "18",  # 18 = Tree Ring
        "searchAll": keyword,
    }
    
    query_string = urllib.parse.urlencode(params)
    url = f"{SEARCH_API_URL}?{query_string}"
    
    logger.info("Querying ITRDB: %s", url)
    
    req = urllib.request.Request(
        url, 
        headers={"User-Agent": "Dendrochronology-Analysis-Platform/2.0"}
    )
    
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            if response.status != 200:
                logger.error("ITRDB API returned status %d", response.status)
                return []
                
            data = json.loads(response.read().decode('utf-8'))
            
            studies = data.get("study", [])
            if not isinstance(studies, list):
                # Sometimes a single result is a dict, not a list
                studies = [studies]
                
            results = []
            for study in studies[:limit]:
                # Extract metadata safely
                s_id = str(study.get("xmlId", ""))
                s_name = study.get("studyName", "Unknown Study")
                
                # Investigators
                inv_data = study.get("investigator", [])
                if isinstance(inv_data, list):
                    inv_names = [i.get("NAME", "Unknown") for i in inv_data if isinstance(i, dict)]
                elif isinstance(inv_data, dict):
                    inv_names = [inv_data.get("NAME", "Unknown")]
                else:
                    inv_names = ["Unknown"]
                investigators = ", ".join(inv_names)
                
                # Site and Species from site list
                sites = study.get("site", [])
                if isinstance(sites, dict):
                    sites = [sites]
                    
                site_name = "Unknown"
                species = "Unknown"
                
                if sites:
                    first_site = sites[0]
                    site_name = first_site.get("siteName", "Unknown")
                    
                    paleo_data = first_site.get("paleoData", [])
                    if isinstance(paleo_data, dict):
                        paleo_data = [paleo_data]
                    
                    if paleo_data:
                        first_data = paleo_data[0]
                        species = first_data.get("species", "Unknown")
                        
                # Time bounding
                earliest = study.get("earliestYear", "Unknown")
                latest = study.get("mostRecentYear", "Unknown")
                
                # Try to find an .rwl download link
                rwl_url = None
                online_links = study.get("onlineResourceLink", [])
                if isinstance(online_links, dict):
                    online_links = [online_links]
                    
                for link in online_links:
                    url_str = link.get("URL", "")
                    if url_str.lower().endswith(".rwl"):
                        rwl_url = url_str
                        break
                        
                results.append(ITRDBStudy(
                    study_id=s_id,
                    study_name=s_name,
                    investigators=investigators,
                    site_name=site_name,
                    species=species,
                    earliest_year=earliest,
                    most_recent_year=latest,
                    rwl_url=rwl_url
                ))
                
            return results
            
    except Exception as e:
        logger.exception("Failed to query ITRDB API")
        return []

def fetch_itrdb_series(url: str) -> list[RingWidthSeries]:
    """Download an RWL file from a URL and parse it.
    
    Args:
        url: The direct URL to an .rwl file
        
    Returns:
        List of parsed RingWidthSeries.
    """
    logger.info("Downloading series from %s", url)
    
    req = urllib.request.Request(
        url, 
        headers={"User-Agent": "Dendrochronology-Analysis-Platform/2.0"}
    )
    
    import tempfile
    import os
    
    try:
        # Download to a temporary file
        with urllib.request.urlopen(req, timeout=15) as response:
            if response.status != 200:
                raise RuntimeError(f"Failed to download data: HTTP {response.status}")
                
            content = response.read()
            
        with tempfile.NamedTemporaryFile(suffix=".rwl", delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
            
        try:
            # Parse the temp file using the Tucson parser
            series_list = read_tucson(tmp_path)
            
            # Append URL to metadata
            for s in series_list:
                s.metadata["source_url"] = url
                
            return series_list
        finally:
            # Clean up
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
                
    except Exception as e:
        logger.exception("Failed to fetch or parse series from %s", url)
        raise RuntimeError(f"Could not load data: {e}") from e
