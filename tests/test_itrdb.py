import json
import urllib.request
from unittest.mock import patch, MagicMock

import pytest

from dendro.io.itrdb import search_itrdb, ITRDBStudy

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
                "investigator": [{"NAME": "Dr. Smith"}],
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
