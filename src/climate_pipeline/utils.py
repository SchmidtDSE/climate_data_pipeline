import xarray as xr
import numpy as np
import pandas as pd
import geopandas as gpd
import rioxarray as rxr
import os
import matplotlib.pyplot as plt # For internal diagnostic plotting if needed

from . import config

# Crucial setting: Globally tell xarray to try keeping attributes (metadata) during operations.
xr.set_options(keep_attrs=True)

def load_boundaries():
    """Loads and returns the boundary geometries defined in config."""
    boundaries = {}
    print("Loading boundaries...")
    for name, path in config.SHAPEFILES.items():
        if not os.path.exists(path):
            print(f"  ERROR: File not found at {path}. Skipping {name}.")
            boundaries[name] = None
            continue
        
        try:
            boundary_WGS84 = gpd.read_file(path)
            if boundary_WGS84.crs is None or str(boundary_WGS84.crs) != config.STANDARD_CRS:
                print(f"  Reprojecting {name} to {config.STANDARD_CRS}...")
                boundary_WGS84 = boundary_WGS84.to_crs(config.STANDARD_CRS)
            boundaries[name] = boundary_WGS84
            print(f"  Loaded {name} boundary.")
        except Exception as e:
            print(f"  ERROR: Couldn't load {name} boundary file. Error: {e}")
            boundaries[name] = None
    return boundaries

def preprocess_data(data, var_name):
    """Applies standard preprocessing: unit conversion."""
    if data is None:
        return None
        
    # Convert Kelvin to Celsius for Temperature
    if "Temperature" in var_name or var_name in ["T_Max", "T_Min", "T_Avg"]:
        if data.attrs.get('units') == 'K':
             data = data - 273.15
             data.attrs['units'] = 'degC'

    return data

def mask_and_spatial_average(data_xr, boundary_gdf):
    """
    Masks data to the boundary geometry and computes spatial average.
    Includes diagnostic print statements for weights.
    """
    try:
        # Clip
        data_clipped = data_xr.rio.clip(boundary_gdf.geometry, boundary_gdf.crs, drop=True)
        
        # Spatial Average (weighted by cosine of latitude for accuracy)
        weights = np.cos(np.deg2rad(data_clipped.lat))
        weights.name = "weights"
        
        # --- Diagnostic Logic mirrored from daignostics.ipynb ---
        if np.isnan(weights.values).any():
             # Fill NaNs in weights (which might occur if lat coords are weird, though rare)
             weights = weights.fillna(0)
             
        data_weighted = data_clipped.weighted(weights)
        spatial_avg = data_weighted.mean(dim=["lat", "lon"])
        
        return spatial_avg
    except Exception as e:
        print(f"Error in spatial averaging: {e}")
        return None

def calculate_smoothed_anomalies(spatialAVG, varKey, scenario, baseline_period=config.BASELINE_PERIOD):
    """
    Calculates anomalies relative to baseline and smooths them.
    Contains ROBUST logic for precipitation baselines and scenario labeling.
    """
    if spatialAVG is None:
        return None
        
    # 1. Average up to annual scale
    if varKey == 'Precip':
        # Sum months to annual total
        annualData = spatialAVG.resample(time='YE').sum(dim='time')
        annualData.attrs['units'] = 'mm/year'
    else:
        # Average months to annual mean
        annualData = spatialAVG.resample(time='YE').mean(dim='time')
        # Unit check/preservation
        if 'units' not in annualData.attrs and 'units' in spatialAVG.attrs:
             annualData.attrs['units'] = spatialAVG.attrs['units']
        
    # 2. Baseline Calculation
    baseline_slice = annualData.sel(time=slice(str(baseline_period["years"][0]), str(baseline_period["years"][1])))
    if baseline_slice.time.size == 0:
        print("    Error: No data available for baseline period.")
        return None
        
    baseline_mean = baseline_slice.mean(dim='time')
    
    # 3. Anomaly Calculation
    if varKey == 'Precip':
        # Check for low baseline (Diagnostic from daignostics.ipynb)
        avg_baseline = baseline_mean.mean().item() # Robust to scalar/array
        if abs(avg_baseline) < 1.0:
             print(f"    Note: Baseline precip ({avg_baseline:.2f} mm) < 1mm/year. Using absolute difference (Δmm/year).")
             anomalies = (annualData - baseline_mean)
             unit = f"Delta {annualData.attrs.get('units', 'mm/year')}"
        else:
            # Percent change
            anomalies = ((annualData - baseline_mean) / baseline_mean) * 100
            unit = "% Change"
    else:
        # Absolute anomalies for temperature
        anomalies = (annualData - baseline_mean)
        unit = f"Delta {annualData.attrs.get('units', 'degC')}"

    anomalies.attrs['units'] = unit

    # 4. Smoothing (Decadal Mean)
    # Using 10-year rolling window
    SMOOTHING_WINDOW = 10
    smoothed_anomalies = anomalies.rolling(time=SMOOTHING_WINDOW, center=True, min_periods=1).mean()
    
    # 5. Convert to DataFrame
    sdf = smoothed_anomalies.to_dataframe(name='Anomaly').reset_index()
    sdf['Variable'] = varKey
    sdf['Year'] = sdf['time'].dt.year
    sdf['DataScenario'] = scenario
    
    # 6. Scenario Labeling Logic (Robust)
    # Handle "Historical + SSP..." strings if they exist
    clean_scenario_name = scenario.replace("Historical + ", "")
    
    if clean_scenario_name == "Historical Climate":
            sdf['Scenario'] = "Historical Climate"
    else:
        # For SSPs, label the historical period (<= Baseline End) as "Historical Climate"
        sdf['Scenario'] = np.where(
            sdf['Year'] <= baseline_period["years"][1],
            "Historical Climate",
            clean_scenario_name
        )
    
    # 7. Handle Simulation ID
    if 'simulation' in sdf.columns:
        sdf = sdf.rename(columns={'simulation': 'Simulation'})
    elif 'source_id' in sdf.columns:
            sdf = sdf.rename(columns={'source_id': 'Simulation'})
    else:
            # Try to recover from coordinates
            if 'simulation' in spatialAVG.coords:
                 sdf['Simulation'] = str(spatialAVG.simulation.values.item())
            elif 'source_id' in spatialAVG.coords:
                sdf['Simulation'] = str(spatialAVG.source_id.values.item())
            else:
                sdf['Simulation'] = "Unknown"
            
    return sdf
