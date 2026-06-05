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
import urllib.error
import urllib.request
import urllib.parse
from dataclasses import dataclass

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

def search_itrdb(keyword: str, limit: int = 30) -> list[ITRDBStudy]:
    """Search the ITRDB via NOAA API for tree ring data.
    
    Args:
        keyword: Search term (e.g., 'oak', 'colorado', 'douglas fir')
        limit: Max results to return
        
    Returns:
        A list of parsed ITRDBStudy objects.
    """
    params: dict[str, str] = {
        "dataPublisher": "NOAA",
        "dataTypeId": "18",  # 18 = Tree Ring
        "searchAll": keyword,
        "limit": str(limit),  # Tell the API to limit results server-side
    }
    
    query_string = urllib.parse.urlencode(params)
    url = f"{SEARCH_API_URL}?{query_string}"
    
    logger.info("Querying ITRDB: %s", url)
    
    req = urllib.request.Request(
        url, 
        headers={"User-Agent": "Fritts/3.0"}
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
                
                # Investigators — the real API returns a comma-separated string
                # ("investigators") or an array of detail objects ("investigatorDetails"),
                # not the "investigator" array of {NAME} dicts the original code expected.
                inv_raw = study.get("investigators")
                if isinstance(inv_raw, str) and inv_raw.strip():
                    investigators = inv_raw.strip()
                else:
                    inv_details = study.get("investigatorDetails", [])
                    if isinstance(inv_details, list):
                        inv_names = []
                        for p in inv_details:
                            if isinstance(p, dict):
                                first = p.get("firstName", "")
                                last = p.get("lastName", "")
                                name = f"{first} {last}".strip()
                                if name:
                                    inv_names.append(name)
                        investigators = ", ".join(inv_names) if inv_names else "Unknown"
                    else:
                        investigators = "Unknown"
                
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
                        raw_species = first_data.get("species", "Unknown")
                        if isinstance(raw_species, list):
                            # API returns array of {scientificName, speciesCode, ...}
                            names = []
                            for s in raw_species:
                                if isinstance(s, dict):
                                    name = s.get("scientificName") or s.get("commonName")
                                    if isinstance(name, list):
                                        name = name[0] if name else ""
                                    if name:
                                        names.append(name)
                                elif isinstance(s, str):
                                    names.append(s)
                            species = "; ".join(names) if names else "Unknown"
                        elif isinstance(raw_species, str):
                            species = raw_species if raw_species else "Unknown"
                        
                # Time bounding — API may return CE-dated fields
                earliest = study.get("earliestYear")
                if earliest is None:
                    earliest = study.get("earliestYearCE", "Unknown")
                latest = study.get("mostRecentYear")
                if latest is None:
                    latest = study.get("mostRecentYearCE", "Unknown")
                
                # Try to find an .rwl download link
                rwl_url = None
                online_links = study.get("onlineResourceLink", [])
                if isinstance(online_links, str):
                    if online_links.lower().endswith(".rwl"):
                        rwl_url = online_links
                elif isinstance(online_links, dict):
                    online_links = [online_links]

                if rwl_url is None and isinstance(online_links, list):
                    for link in online_links:
                        if isinstance(link, dict):
                            url_str = link.get("URL", "")
                        elif isinstance(link, str):
                            url_str = link
                        else:
                            continue
                        if url_str.lower().endswith(".rwl"):
                            rwl_url = url_str
                            break

                # Fallback: scan dataFile entries inside site.paleoData for .rwl URLs
                if rwl_url is None and isinstance(sites, list):
                    for site_entry in sites:
                        paleo_data = site_entry.get("paleoData", []) if isinstance(site_entry, dict) else []
                        if isinstance(paleo_data, dict):
                            paleo_data = [paleo_data]
                        for pd_entry in paleo_data:
                            if not isinstance(pd_entry, dict):
                                continue
                            for df in pd_entry.get("dataFile", []):
                                f_url = df.get("fileUrl", "") if isinstance(df, dict) else ""
                                if f_url.lower().endswith(".rwl"):
                                    rwl_url = f_url
                                    break
                            if rwl_url:
                                break
                        if rwl_url:
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
            
    except urllib.error.HTTPError as e:
        logger.error("ITRDB API returned HTTP %d: %s", e.code, e.reason)
        return []
    except urllib.error.URLError as e:
        logger.error("ITRDB API connection failed: %s", e.reason)
        return []
    except Exception:
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
        headers={"User-Agent": "Fritts/3.0"}
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
