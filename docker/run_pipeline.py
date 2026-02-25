"""
Headless full climate data extraction.

Equivalent to Full_Data_Extraction.ipynb but runs without Jupyter.

Usage:
    python docker/run_pipeline.py
    python docker/run_pipeline.py --parks JoshuaTree
    python docker/run_pipeline.py --n-workers 30 --worker-vm n1-highmem-4
"""

import argparse
import os
import sys
import time

import coiled
import pandas as pd

from andrewAdaptLibrary import (
    CatalogExplorer,
    get_climate_data,
    load_boundary,
    get_lat_lon_bounds,
    VARIABLE_MAP,
    SCENARIO_MAP,
)

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

PARK_SHAPEFILES = {
    "JoshuaTree": os.path.join(PROJECT_ROOT, "parkOutlines", "JoshuaTree", "Joshua_Tree_National_Park.shp"),
    "Mojave": os.path.join(PROJECT_ROOT, "parkOutlines", "Mojave", "Mojave_National_Preserve.shp"),
}


def parse_args():
    parser = argparse.ArgumentParser(description="Full climate data extraction pipeline")
    parser.add_argument("--parks", nargs="+", default=list(PARK_SHAPEFILES.keys()),
                        help="Parks to process (default: all)")
    parser.add_argument("--variables", nargs="+", default=["T_Max", "T_Min"],
                        help="Variables to fetch (default: T_Max T_Min)")
    parser.add_argument("--n-workers", type=int, default=7,
                        help="Number of Coiled workers (default: 7)")
    parser.add_argument("--worker-vm", type=str, default="n1-highmem-4",
                        help="GCP VM type for workers (default: n1-highmem-4)")
    parser.add_argument("--region", type=str, default="us-west1",
                        help="GCP region (default: us-west1)")
    parser.add_argument("--output-dir", type=str,
                        default=os.path.join(PROJECT_ROOT, "data", "csv", "full_extraction"),
                        help="Output directory for CSVs")
    return parser.parse_args()


def main():
    args = parse_args()
    os.makedirs(args.output_dir, exist_ok=True)

    variables = args.variables
    historical_scenarios = ["Historical Climate"]
    future_scenarios = ["SSP 2-4.5", "SSP 3-7.0", "SSP 5-8.5"]

    # Load boundaries
    boundaries = {}
    for name in args.parks:
        if name not in PARK_SHAPEFILES:
            print(f"Unknown park: {name}. Available: {list(PARK_SHAPEFILES.keys())}")
            sys.exit(1)
        boundaries[name] = load_boundary(PARK_SHAPEFILES[name])
        lat, lon = get_lat_lon_bounds(boundaries[name])
        print(f"{name}: {lat[0]:.2f}-{lat[1]:.2f}°N, {abs(lon[0]):.2f}-{abs(lon[1]):.2f}°W")

    # Start cluster
    print(f"\nStarting {args.n_workers}-worker cluster on GCP {args.region}...")
    t_cluster_start = time.perf_counter()

    cluster = coiled.Cluster(
        name="full-extraction",
        region=args.region,
        n_workers=args.n_workers,
        worker_vm_types=[args.worker_vm],
        spot_policy="spot_with_fallback",
        idle_timeout="30 minutes",
        package_sync=True,
    )
    client = cluster.get_client()
    t_cluster_ready = time.perf_counter()

    print(f"Cluster ready in {t_cluster_ready - t_cluster_start:.0f}s")
    print(f"  Workers: {len(client.scheduler_info()['workers'])}")
    print(f"  Dashboard: {client.dashboard_link}")

    # Fetch data
    all_timings = {}
    t_total_start = time.perf_counter()

    try:
        for park_name, boundary in boundaries.items():
            print(f"\n{'='*60}")
            print(f"  {park_name}")
            print(f"{'='*60}")

            park_dfs = {var: [] for var in variables}

            # Historical: 1950-2014
            print(f"\n  Fetching Historical (1950-2014)...")
            t0 = time.perf_counter()

            hist_data = get_climate_data(
                variables=variables,
                scenarios=historical_scenarios,
                boundary=boundary,
                time_slice=(1950, 2014),
                timescale="monthly",
                backend="coiled",
                coiled_cluster=cluster,
            )

            t_hist = time.perf_counter() - t0
            all_timings[f"{park_name}_historical"] = t_hist

            for var in variables:
                df = hist_data[var]
                print(f"    {var}: {len(df):,} rows")
                park_dfs[var].append(df)
            print(f"  Historical done in {t_hist:.1f}s")

            # Future SSPs: 2015-2100
            print(f"\n  Fetching SSP scenarios (2015-2100)...")
            t0 = time.perf_counter()

            future_data = get_climate_data(
                variables=variables,
                scenarios=future_scenarios,
                boundary=boundary,
                time_slice=(2015, 2100),
                timescale="monthly",
                backend="coiled",
                coiled_cluster=cluster,
            )

            t_future = time.perf_counter() - t0
            all_timings[f"{park_name}_future"] = t_future

            for var in variables:
                df = future_data[var]
                print(f"    {var}: {len(df):,} rows")
                park_dfs[var].append(df)
            print(f"  Future scenarios done in {t_future:.1f}s")

            # Combine and save
            print(f"\n  Saving CSVs...")
            for var in variables:
                combined = pd.concat(park_dfs[var], ignore_index=True)
                combined["park"] = park_name
                filename = f"{park_name}_{var}.csv"
                filepath = os.path.join(args.output_dir, filename)
                combined.to_csv(filepath, index=False)
                print(f"    Saved: {filename} ({len(combined):,} rows)")

        t_total = time.perf_counter() - t_total_start

        # Compute T_Avg if we have both T_Max and T_Min
        if "T_Max" in variables and "T_Min" in variables:
            print(f"\n{'='*60}")
            print(f"  Computing T_Avg")
            print(f"{'='*60}")
            for park_name in boundaries:
                tmax = pd.read_csv(os.path.join(args.output_dir, f"{park_name}_T_Max.csv"))
                tmin = pd.read_csv(os.path.join(args.output_dir, f"{park_name}_T_Min.csv"))
                merge_cols = ["simulation", "time", "scenario", "timescale", "park"]
                merged = tmax.merge(tmin[merge_cols + ["T_Min"]], on=merge_cols)
                merged["T_Avg"] = (merged["T_Max"] + merged["T_Min"]) / 2
                out_path = os.path.join(args.output_dir, f"{park_name}_T_Avg.csv")
                merged.to_csv(out_path, index=False)
                print(f"  {park_name}_T_Avg.csv: {len(merged):,} rows")

        # Print summary
        print(f"\n{'='*60}")
        print(f"  TIMING SUMMARY")
        print(f"{'='*60}")
        print(f"Cluster spin-up: {t_cluster_ready - t_cluster_start:.0f}s")
        for label, t in all_timings.items():
            print(f"  {label}: {t:.1f}s ({t/60:.1f} min)")
        print(f"Total data fetch: {t_total:.1f}s ({t_total/60:.1f} min)")
        print(f"Total including cluster: {t_cluster_ready - t_cluster_start + t_total:.0f}s")
        print(f"\nOutput: {args.output_dir}")

    finally:
        cluster.close()
        print("Cluster shut down.")


if __name__ == "__main__":
    main()
