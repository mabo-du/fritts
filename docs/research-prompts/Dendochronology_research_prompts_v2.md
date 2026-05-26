# Deep Research Prompts — Dendrochronology Analysis Platform

I am building an open-source desktop application for tree-ring cross-dating, measurement, and master chronology building. Existing software in this field is often dated, proprietary, or lacks a modern visual interface. The tool is targeting dendrochronologists working with archaeological timbers, climate researchers building proxy records, and wood specialists in heritage contexts.

The planned tech stack is Python, PyQt6, PyQtGraph, Pandas, NumPy, and SciPy. The MVP covers importing standard ring-width formats, interactive visual plotting, statistical cross-dating, and basic master chronology generation. Later versions will add image-based measurement and ITRDB integration.

---

## RESEARCH PROMPT 1 — Tree-Ring Data Formats

What are the standard file formats used for storing dendrochronology data, including the Tucson decadal format (.rwl, .tuc), the Heidelberg format, and TRiDaS (Tree Ring Data Standard)?

- Provide a detailed breakdown of each format's structure, including how ring-width values, metadata, and sample identifiers are encoded.
- How does TRiDaS structure metadata specifically for archaeological timber (e.g., provenance, species, sapwood presence)?
- Are there any lesser-known or regional formats still in active use that an importer should handle (e.g., Nottingham, CATRAS)?
- What edge cases or common malformations appear in real-world .rwl files that a parser needs to handle gracefully?
- Are there existing open-source Python libraries for parsing these formats (e.g., `dplR`-style readers ported to Python), or would a parser need to be written from scratch?

---

## RESEARCH PROMPT 2 — Cross-dating Algorithms

What statistical algorithms are used to cross-match tree-ring width sequences against master chronologies, and how are they implemented in practice?

- Explain the full mathematics behind the **t-value** in both its Baillie-Pilcher and Hollstein variants — what do they measure, how do they differ, and what are their known weaknesses?
- Explain **Gleichläufigkeit (GLK)** — the Coefficient of Parallel Variation — including how it is calculated, what threshold values are considered significant, and how it complements or conflicts with the t-value.
- What is the role of **cross-correlation** and sliding window correlation in cross-dating, and how does it relate to the above?
- Are there more modern statistical approaches (e.g., Rbar, EPS, signal-free standardization) that are considered superior or complementary to these classic measures?
- How are **false positives** (spurious high scores at incorrect positions) typically detected or filtered?
- What are the recommended minimum series lengths and overlap requirements for each algorithm to produce reliable results?
- Are there reference implementations of these algorithms in Python or R that could inform or be adapted for this project?

---

## RESEARCH PROMPT 3 — Image Processing for Ring-Width Measurement

What computer vision and image analysis techniques are used to detect and measure tree-ring boundaries from high-resolution scans of wood cores or cross-sections?

- What are the standard imaging approaches used in labs today — flatbed scanners, microscope cameras, line cameras — and what resolution and colour depth are typically required?
- What classical image processing techniques (edge detection, thresholding, gradient analysis) are effective for ring boundary detection, and what are their limitations on difficult samples (reaction wood, frost rings, false rings)?
- Are there deep learning or CNN-based approaches that have been published or applied to this problem? What datasets exist for training such models?
- What semi-automated approaches exist that combine algorithmic detection with human correction — and what UI patterns work best for that correction workflow?
- Are there existing open-source tools or libraries (e.g., OpenCV pipelines, ImageJ plugins) that handle any part of this workflow and could be integrated or referenced?
- How is the physical scale (micrometres per pixel) typically calibrated and embedded in measurement data?

---

## RESEARCH PROMPT 4 — Existing Dendrochronology Software

What software tools are currently used in dendrochronology labs, and what are the known pain points for their users?

- Provide an overview of the major tools: **TSAP-Win**, **CooRecorder/CDendro**, **Tellervo**, **COFECHA**, **dplR** (R package), **PAST**, and any others in active use.
- For each tool, note: licensing model (proprietary/open), platform support, primary use case, and approximate age/last update.
- What are the most commonly cited frustrations among dendrochronologists and archaeologists using these tools? (Consider usability, file format lock-in, lack of scripting, poor visualisation, Windows-only constraints, etc.)
- Are there any recently emerged or in-development tools that represent the current state of the art?
- What features do users most frequently request that existing tools lack?
- Are there published user studies, forum discussions, or community surveys that document these pain points?

---

## RESEARCH PROMPT 5 — Master Chronology Databases and APIs

Where are master regional tree-ring chronologies hosted, and how can they be accessed programmatically?

- Provide a detailed overview of the **International Tree-Ring Data Bank (ITRDB)** — its scope, data organisation, and the formats in which chronologies are distributed.
- Does the ITRDB offer a REST API, OAI-PMH endpoint, or other programmatic access method? If so, document the query parameters, rate limits, authentication requirements, and response formats.
- Are there other significant chronology databases (e.g., **DCCD** — Dutch Centre for Dendrochronology; **BDN** — Bois & Dendrochronologie; regional European databases) and do they offer API access?
- What are the metadata fields available in ITRDB records that are useful for filtering by region, species, time period, or data type?
- Are there known data quality issues in the ITRDB that a consuming application should handle (missing values, inconsistent dating, format variations)?
- What licensing or attribution requirements apply to ITRDB data when used in open-source software?

---

## RESEARCH PROMPT 6 — UI and UX for Visual Cross-dating

What are the best interaction design patterns for visually aligning and editing long time-series data in the context of dendrochronology?

- How should a UI handle **zooming and panning** across ring-width curves that may span several centuries, while keeping multiple overlaid series visually legible?
- What are effective UX patterns for **shifting a series forward or backward in time** to search for the best cross-dating position — including keyboard shortcuts, drag handles, and live statistical feedback during the shift?
- How should the UI handle **adding or removing phantom rings** (inserting or deleting a year at a specific position) — a core part of the cross-dating correction workflow?
- What visual encoding works best for showing **match quality** across all tested offset positions — e.g., a sliding window score plot beneath the main series view?
- Are there well-designed open-source time-series tools (in any domain — finance, bioinformatics, geophysics) whose interaction patterns could be adapted for this use case?
- What accessibility considerations apply — e.g., for users with colour vision deficiency when comparing overlaid curves, or for users working with very high-DPI displays?
- How should the UI handle **undo/redo** for destructive edits like ring insertion, deletion, or series re-dating?

---

## RESEARCH PROMPT 7 — Detrending and Standardisation

What methods are used to remove biological growth trends from raw ring-width series, and why does this matter for master chronology building?

- Explain the purpose of detrending in dendrochronology — why raw ring widths cannot simply be averaged across samples of different ages or sizes.
- What are the standard detrending methods: **negative exponential fitting**, **cubic spline detrending**, **Hugershoff curve**, **regionalisation curve standardisation (RCS)**, and **signal-free standardisation**? Explain the mathematical basis of each and when each is most appropriate.
- What is the **Ring-Width Index (RWI)** and how is it calculated from raw measurements?
- What are the known pitfalls of over-detrending (the "segment length curse") and how do researchers guard against it?
- Are there Python implementations of these methods (e.g., via SciPy curve fitting), or would they need to be implemented from scratch?
- At what point in the workflow should detrending occur — before or after cross-dating — and does the order matter?

---

## RESEARCH PROMPT 8 — Python Ecosystem and Performance Considerations

What Python libraries, architectural patterns, and performance strategies are most relevant to building this tool?

- What are the strengths and limitations of **PyQtGraph** for rendering long time-series data with interactive zoom and pan? Are there known performance ceilings (e.g., series length, number of overlaid curves) and how are they typically worked around?
- Are there alternative Python visualisation libraries (e.g., **pyqtgraph vs matplotlib embedded in Qt vs vispy**) that would be better suited to the interactive, real-time demands of this application?
- How should **Pandas and NumPy** data structures be designed to hold ring-width series with associated metadata (series ID, start year, species, site) in a way that is efficient for the cross-dating sliding window computations?
- What **packaging and distribution** strategies work well for Python desktop apps targeting researchers on Windows, macOS, and Linux — e.g., PyInstaller, cx_Freeze, conda-forge, flatpak?
- Are there any existing open-source Python dendrochronology projects (partial or complete) on GitHub or PyPI that could serve as a foundation or reference?
