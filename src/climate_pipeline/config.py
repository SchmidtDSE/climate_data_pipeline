import os

# --- Constants & Configuration ---

# Coordinate Reference System
STANDARD_CRS = "EPSG:4326"  # WGS84

# Downscaling Parameters
DOWNSCALING = "Statistical"
RES = "3 km"

# Variables specific to Statistical downscaling
VARIABLES_STAT = {
    "T_Max": "Maximum air temperature at 2m",
    "T_Min": "Minimum air temperature at 2m",
    "Precip": "Precipitation (total)"
}

# Scenarios required for the plots
SCENARIOS = ["Historical Climate", "SSP 2-4.5", "SSP 3-7.0", "SSP 5-8.5"]

# Define 30-year Climatology Periods
BASELINE_PERIOD = {"name": "Baseline (1985-2014)", "years": (1985, 2014)}
FUTURE_PERIOD = {"name": "Late-Century (2070-2099)", "years": (2070, 2099)}
TIMESPAN = (BASELINE_PERIOD["years"][0], FUTURE_PERIOD["years"][1])

# Shapefile Paths (Relative to the project root typically)
# These paths assume you are running from the project root or notebooks folder.
# We will use absolute paths or robust relative path handling in the notebooks.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SHAPEFILES = {
    "JoshuaTree": os.path.join(BASE_DIR, "JoshuaTreeOutlines", "JoshuaTree", "Joshua_Tree_National_Park.shp"),
    "Mojave": os.path.join(BASE_DIR, "Mojave", "Mojave_National_Preserve.shp")
}
