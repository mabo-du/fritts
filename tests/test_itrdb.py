import json
import urllib.request
from unittest.mock import patch, MagicMock

import pytest

from dendro.io.itrdb import search_itrdb, ITRDBStudy, fetch_itrdb_series

@patch('urllib.request.urlopen')
def test_search_itrdb_success(mock_urlopen):
    # Mock API response
    mock_response = MagicMock()
    mock_response.status = 200
    
    mock_data = {
        "study": [
            {
                "xmlId": "1234",
                "studyName": "Test Study",
                "investigators": "Dr. Smith",
                "site": {
                    "siteName": "Test Site",
                    "paleoData": {"species": "Quercus alba"}
                },
                "earliestYear": 1000,
                "mostRecentYear": 2000,
                "onlineResourceLink": [
                    {"URL": "https://example.com/data.rwl"}
                ]
            }
        ]
    }
    mock_response.read.return_value = json.dumps(mock_data).encode('utf-8')
    mock_urlopen.return_value.__enter__.return_value = mock_response

    results = search_itrdb("oak")
    
    assert len(results) == 1
    study = results[0]
    assert study.study_id == "1234"
    assert study.study_name == "Test Study"
    assert study.investigators == "Dr. Smith"
    assert study.site_name == "Test Site"
    assert study.species == "Quercus alba"
    assert study.earliest_year == 1000
    assert study.most_recent_year == 2000
    assert study.rwl_url == "https://example.com/data.rwl"

@patch('urllib.request.urlopen')
def test_search_itrdb_empty(mock_urlopen):
    # Mock empty response
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.read.return_value = json.dumps({"study": []}).encode('utf-8')
    mock_urlopen.return_value.__enter__.return_value = mock_response

    results = search_itrdb("nonexistent")
    assert len(results) == 0

@patch('urllib.request.urlopen')
def test_search_itrdb_error(mock_urlopen):
    # Mock HTTP error
    mock_response = MagicMock()
    mock_response.status = 500
    mock_urlopen.return_value.__enter__.return_value = mock_response

    results = search_itrdb("oak")
    assert len(results) == 0

@patch('urllib.request.urlopen')
def test_search_itrdb_online_link_string(mock_urlopen):
    """onlineResourceLink as a plain string (the real NOAA API shape)."""
    mock_response = MagicMock()
    mock_response.status = 200
    mock_data = {
        "study": [
            {
                "xmlId": "5678",
                "studyName": "Oak Study",
                "investigators": "Dr. Jones",
                "site": {
                    "siteName": "Oak Forest",
                    "paleoData": {"species": "Quercus"}
                },
                "earliestYear": 1500,
                "mostRecentYear": 2000,
                "onlineResourceLink": "https://example.com/data.rwl"
            }
        ]
    }
    mock_response.read.return_value = json.dumps(mock_data).encode('utf-8')
    mock_urlopen.return_value.__enter__.return_value = mock_response

    results = search_itrdb("oak")
    assert len(results) == 1
    assert results[0].rwl_url == "https://example.com/data.rwl"

@patch('urllib.request.urlopen')
def test_search_itrdb_online_link_string_no_rwl(mock_urlopen):
    """onlineResourceLink as a plain string that isn't .rwl — should not crash."""
    mock_response = MagicMock()
    mock_response.status = 200
    mock_data = {
        "study": [
            {
                "xmlId": "9999",
                "studyName": "Climate Study",
                "investigators": "Dr. X",
                "site": {
                    "siteName": "Some Site",
                    "paleoData": {"species": "Pinus"}
                },
                "earliestYear": 1800,
                "mostRecentYear": 2000,
                "onlineResourceLink": "https://www.ncei.noaa.gov/access/paleo-search/study/9999"
            }
        ]
    }
    mock_response.read.return_value = json.dumps(mock_data).encode('utf-8')
    mock_urlopen.return_value.__enter__.return_value = mock_response

    results = search_itrdb("pine")
    assert len(results) == 1
    assert results[0].rwl_url is None

@patch('urllib.request.urlopen')
def test_search_itrdb_data_file_rwl(mock_urlopen):
    """.rwl URL found in site.paleoData.dataFile.fileUrl fallback."""
    mock_response = MagicMock()
    mock_response.status = 200
    mock_data = {
        "study": [
            {
                "xmlId": "4444",
                "studyName": "Tree Ring Study",
                "investigators": "Dr. Tree",
                "site": [{
                    "siteName": "Forest",
                    "paleoData": [{
                        "species": "Picea",
                        "dataFile": [
                            {"fileUrl": "https://example.com/study.rwl", "urlDescription": "RWL File"},
                            {"fileUrl": "https://example.com/notes.txt", "urlDescription": "Notes"}
                        ]
                    }]
                }],
                "earliestYear": 1700,
                "mostRecentYear": 2000,
                "onlineResourceLink": "https://www.ncei.noaa.gov/access/paleo-search/study/4444"
            }
        ]
    }
    mock_response.read.return_value = json.dumps(mock_data).encode('utf-8')
    mock_urlopen.return_value.__enter__.return_value = mock_response

    results = search_itrdb("spruce")
    assert len(results) == 1
    assert results[0].rwl_url == "https://example.com/study.rwl"

@patch('urllib.request.urlopen')
def test_search_itrdb_no_rwl_anywhere(mock_urlopen):
    """No .rwl URL found anywhere — should return None, not crash."""
    mock_response = MagicMock()
    mock_response.status = 200
    mock_data = {
        "study": [
            {
                "xmlId": "5555",
                "studyName": "No RWL Study",
                "investigators": "Dr. None",
                "site": {
                    "siteName": "Empty",
                    "paleoData": {"species": "Unknown"}
                },
                "earliestYear": 1900,
                "mostRecentYear": 2000,
                "onlineResourceLink": "https://example.com/study-page"
            }
        ]
    }
    mock_response.read.return_value = json.dumps(mock_data).encode('utf-8')
    mock_urlopen.return_value.__enter__.return_value = mock_response

    results = search_itrdb("nothing")
    assert len(results) == 1
    assert results[0].rwl_url is None

@patch('urllib.request.urlopen')
def test_search_itrdb_missing_online_link(mock_urlopen):
    """No onlineResourceLink key at all — should not crash."""
    mock_response = MagicMock()
    mock_response.status = 200
    mock_data = {
        "study": [
            {
                "xmlId": "6666",
                "studyName": "No Links",
                "investigators": "Dr. Missing",
                "site": {"siteName": "Nowhere"},
                "earliestYear": 1900,
                "mostRecentYear": 2000
            }
        ]
    }
    mock_response.read.return_value = json.dumps(mock_data).encode('utf-8')
    mock_urlopen.return_value.__enter__.return_value = mock_response

    results = search_itrdb("missing")
    assert len(results) == 1
    assert results[0].rwl_url is None

@patch('urllib.request.urlopen')
def test_search_itrdb_investigator_details(mock_urlopen):
    """investigatorDetails array fallback (real API format)."""
    mock_response = MagicMock()
    mock_response.status = 200
    mock_data = {
        "study": [
            {
                "xmlId": "7777",
                "studyName": "Details Study",
                "investigatorDetails": [
                    {"firstName": "Jane", "lastName": "Doe"},
                    {"firstName": "John", "lastName": "Smith"}
                ],
                "site": {"siteName": "Forest"},
                "earliestYear": 1600,
                "mostRecentYear": 2000,
                "onlineResourceLink": "https://example.com/study-page"
            }
        ]
    }
    mock_response.read.return_value = json.dumps(mock_data).encode('utf-8')
    mock_urlopen.return_value.__enter__.return_value = mock_response

    results = search_itrdb("details")
    assert len(results) == 1
    assert results[0].investigators == "Jane Doe, John Smith"

@patch('urllib.request.urlopen')
def test_search_itrdb_missing_investigators(mock_urlopen):
    """No investigator data at all — should return Unknown, not crash."""
    mock_response = MagicMock()
    mock_response.status = 200
    mock_data = {
        "study": [
            {
                "xmlId": "8888",
                "studyName": "No Investigator",
                "site": {"siteName": "Void"},
                "earliestYear": 1900,
                "mostRecentYear": 2000
            }
        ]
    }
    mock_response.read.return_value = json.dumps(mock_data).encode('utf-8')
    mock_urlopen.return_value.__enter__.return_value = mock_response

    results = search_itrdb("unknown")
    assert len(results) == 1
    assert results[0].investigators == "Unknown"

@patch('urllib.request.urlopen')
def test_search_itrdb_ce_year_fields(mock_urlopen):
    """API uses earliestYearCE/mostRecentYearCE instead of earliestYear/mostRecentYear."""
    mock_response = MagicMock()
    mock_response.status = 200
    mock_data = {
        "study": [
            {
                "xmlId": "9012",
                "studyName": "CE Years Study",
                "investigators": "Dr. CE",
                "site": {"siteName": "Old Site"},
                "earliestYearCE": 900,
                "mostRecentYearCE": 2002,
                "onlineResourceLink": "https://example.com/page"
            }
        ]
    }
    mock_response.read.return_value = json.dumps(mock_data).encode('utf-8')
    mock_urlopen.return_value.__enter__.return_value = mock_response

    results = search_itrdb("ce_test")
    assert len(results) == 1
    assert results[0].earliest_year == 900
    assert results[0].most_recent_year == 2002

@patch('urllib.request.urlopen')
def test_search_itrdb_species_array(mock_urlopen):
    """Species as array of {scientificName, speciesCode} objects."""
    mock_response = MagicMock()
    mock_response.status = 200
    mock_data = {
        "study": [
            {
                "xmlId": "1011",
                "studyName": "Species Array Study",
                "investigators": "Dr. Species",
                "site": {
                    "siteName": "Forest",
                    "paleoData": {
                        "species": [
                            {"speciesCode": "QUST", "scientificName": "Quercus stellata"},
                            {"speciesCode": "QUAL", "scientificName": "Quercus alba"}
                        ]
                    }
                },
                "earliestYear": 1700,
                "mostRecentYear": 2000,
                "onlineResourceLink": "https://example.com/page"
            }
        ]
    }
    mock_response.read.return_value = json.dumps(mock_data).encode('utf-8')
    mock_urlopen.return_value.__enter__.return_value = mock_response

    results = search_itrdb("species_test")
    assert len(results) == 1
    assert "Quercus stellata" in results[0].species
    assert "Quercus alba" in results[0].species

@patch('urllib.request.urlopen')
def test_search_itrdb_api_limit_param(mock_urlopen):
    """Verify the API limit parameter is passed in the request URL."""
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.read.return_value = json.dumps({"study": []}).encode('utf-8')
    mock_urlopen.return_value.__enter__.return_value = mock_response

    search_itrdb("test", limit=10)

    # Check that the URL contains limit=10
    call_url = mock_urlopen.call_args[0][0].full_url
    assert "limit=10" in call_url, f"Expected limit=10 in URL, got: {call_url}"

    search_itrdb("test", limit=25)
    call_url2 = mock_urlopen.call_args[0][0].full_url
    assert "limit=25" in call_url2, f"Expected limit=25 in URL, got: {call_url2}"

@patch('urllib.request.urlopen')
def test_search_itrdb_default_limit(mock_urlopen):
    """Default limit of 30 should be in the API URL (NOAA API fails on >45)."""
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.read.return_value = json.dumps({"study": []}).encode('utf-8')
    mock_urlopen.return_value.__enter__.return_value = mock_response

    search_itrdb("test")
    call_url = mock_urlopen.call_args[0][0].full_url
    assert "limit=30" in call_url, f"Expected limit=30 in URL, got: {call_url}"
