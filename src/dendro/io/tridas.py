"""dendro.io.tridas — Parser for the TRiDaS XML (.xml) format.

exports: read_tridas
used_by:
  dendro.ui.dialogs -> ImportDialog
rules:
  - read_tridas must return list[RingWidthSeries]
  - Fault-tolerant namespace handling.
"""

import logging
from pathlib import Path

import numpy as np
from lxml import etree

from dendro.models.series import RingWidthSeries

logger = logging.getLogger(__name__)

def read_tridas(filepath: str | Path) -> list[RingWidthSeries]:
    """Parse a TRiDaS XML file and return a list of RingWidthSeries."""
    filepath = Path(filepath)
    
    try:
        tree = etree.parse(str(filepath))
        root = tree.getroot()
    except Exception as e:
        logger.error(f"Failed to parse TRiDaS XML {filepath}: {e}")
        return []
        
    result = []
    
    # Find all measurementSeries using local-name to avoid strict namespace matching issues
    series_elements = root.xpath('//*[local-name()="measurementSeries"]')
    
    for idx, series_elem in enumerate(series_elements):
        # ID
        title_elem = series_elem.xpath('./*[local-name()="title"]')
        series_id = title_elem[0].text.strip() if title_elem and title_elem[0].text else f"Series_{idx+1}"
        
        # Start Year
        start_year = 0
        first_year_elem = series_elem.xpath('.//*[local-name()="firstYear"]')
        if first_year_elem and first_year_elem[0].text:
            try:
                start_year = int(first_year_elem[0].text)
                if first_year_elem[0].get("suffix", "") == "BC":
                    start_year = -start_year + 1 # Astronomical
            except ValueError:
                pass
                
        # Values
        widths_list = []
        value_elems = series_elem.xpath('.//*[local-name()="values"]/*[local-name()="value"]')
        for v in value_elems:
            val_text = v.get("value")
            if val_text:
                try:
                    widths_list.append(float(val_text))
                except ValueError:
                    widths_list.append(np.nan)
            else:
                widths_list.append(np.nan)
                
        # Unit and precision
        unit_elems = series_elem.xpath('.//*[local-name()="unit"]')
        multiplier = 100.0
        if unit_elems and unit_elems[0].get("normalTridas"):
            unit = unit_elems[0].get("normalTridas").lower()
            if "micrometre" in unit:
                multiplier = 1000.0
            elif "millimetre" in unit:
                multiplier = 1.0
                
        widths = np.array(widths_list, dtype=np.float64) / multiplier
        
        # Metadata - grab from ancestors
        metadata = {}
        # Try to find species
        taxon_elem = series_elem.xpath('ancestor::*[local-name()="element"]/*[local-name()="taxon"]')
        if taxon_elem and taxon_elem[0].text:
            metadata["species"] = taxon_elem[0].text
            
        series = RingWidthSeries(
            series_id=series_id,
            start_year=start_year,
            widths=widths,
            metadata=metadata
        )
        result.append(series)
        
    return result

def write_tridas(series_list: list[RingWidthSeries], filepath: str | Path) -> None:
    """Export a list of RingWidthSeries to a TRiDaS XML file."""
    filepath = Path(filepath)
    
    # Build TRiDaS tree
    NS = "http://www.tridas.org/1.2.2"
    
    # Custom namespace map to avoid prefixes like ns0:
    nsmap = {None: NS}
    root = etree.Element(f"{{{NS}}}tridas", nsmap=nsmap)
    
    project = etree.SubElement(root, f"{{{NS}}}project")
    
    title = etree.SubElement(project, f"{{{NS}}}title")
    title.text = "Fritts Export"
    
    obj = etree.SubElement(project, f"{{{NS}}}object")
    obj_title = etree.SubElement(obj, f"{{{NS}}}title")
    obj_title.text = "Exported Object"
    
    for s in series_list:
        element = etree.SubElement(obj, f"{{{NS}}}element")
        el_title = etree.SubElement(element, f"{{{NS}}}title")
        el_title.text = s.series_id
        
        taxon = etree.SubElement(element, f"{{{NS}}}taxon")
        taxon.text = s.metadata.get("species", "Unknown")
        
        sample = etree.SubElement(element, f"{{{NS}}}sample")
        sam_title = etree.SubElement(sample, f"{{{NS}}}title")
        sam_title.text = "Sample 1"
        
        radius = etree.SubElement(sample, f"{{{NS}}}radius")
        rad_title = etree.SubElement(radius, f"{{{NS}}}title")
        rad_title.text = "Radius 1"
        
        ms = etree.SubElement(radius, f"{{{NS}}}measurementSeries")
        ms_title = etree.SubElement(ms, f"{{{NS}}}title")
        ms_title.text = s.series_id
        
        # Unit (we store mm, exporting as 1/100 mm for standard)
        # Note: actually "1/100th millimetres" is the TRiDaS normal standard
        meas_var = etree.SubElement(ms, f"{{{NS}}}measuringMethod")
        meas_var.set("normalTridas", "measuring platform")
        
        unit = etree.SubElement(ms, f"{{{NS}}}unit")
        unit.set("normalTridas", "1/100th millimetres")
        
        first_year = etree.SubElement(ms, f"{{{NS}}}firstYear")
        # Handle Astronomical vs Historical for TRiDaS BC
        if s.start_year <= 0:
            first_year.text = str(-s.start_year + 1)
            first_year.set("suffix", "BC")
        else:
            first_year.text = str(s.start_year)
            first_year.set("suffix", "AD")
            
        values_elem = etree.SubElement(ms, f"{{{NS}}}values")
        
        for w in s.widths:
            v_elem = etree.SubElement(values_elem, f"{{{NS}}}value")
            if np.isnan(w):
                v_elem.set("value", "0")
            else:
                v_elem.set("value", str(int(round(w * 100))))
                
    # Write to file
    tree = etree.ElementTree(root)
    tree.write(str(filepath), pretty_print=True, xml_declaration=True, encoding="UTF-8")
