"""export_r.py — Generator for R scripts using the dplR library.

exports: generate_dplr_script
used_by:
  dendro.ui.main_window -> Export menu
rules:
  - Output standard R syntax compatible with dplR.
"""

from __future__ import annotations

from pathlib import Path


def generate_dplr_script(r_filepath: str, tucson_filepath: str) -> None:
    """Generate an R script that loads the exported Tucson file via dplR.
    
    Args:
        r_filepath: The path to save the .R script to.
        tucson_filepath: The path to the Tucson .rwl file that the script will load.
    """
    tucson_name = Path(tucson_filepath).name
    
    script_content = f"""# Auto-generated Dendrochronology Analysis Script
# Requires the 'dplR' package (Dendrochronology Program Library in R)

# 0. Setup Environment
# Set working directory to the location of this script
setwd(dirname(rstudioapi::getActiveDocumentContext()$path))

# Install dplR if not already installed
if (!requireNamespace("dplR", quietly = TRUE)) {{
    install.packages("dplR")
}}
library(dplR)

# 1. Load the Tucson (.rwl) file
data_file <- "{tucson_name}"
cat("Loading data from:", data_file, "\\n")
rwl_data <- read.rwl(data_file)

# 2. View basic summary statistics
print("Summary Statistics:")
summary(rwl_data)

# 3. Plot the raw ring widths (Spaghetti plot)
plot(rwl_data, plot.type="spag", main="Raw Ring Widths")

# 4. Detrend the series using a modified negative exponential curve
# Note: You can change method to "Spline", "Mean", or "ModNegExp"
rwi <- detrend(rwl_data, method="ModNegExp")

# 5. Build the master chronology using a bi-weight robust mean
crn <- chron(rwi, biweight=TRUE)

# 6. Plot the final master chronology with sample depth
plot(crn, add.spline=TRUE, nyrs=32, main="Master Chronology")

# 7. Quality control (COFECHA equivalent)
# Uncomment the line below to run interactive cross-dating quality control
# corr.rwl.seg(rwl_data, seg.length=50, bin.floor=100)
"""

    with open(r_filepath, "w", encoding="utf-8") as f:
        f.write(script_content)
