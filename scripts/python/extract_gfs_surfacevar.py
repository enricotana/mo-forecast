import sys
import getopt
from pathlib import Path

import pandas as pd
import xarray as xr


from tqdm import tqdm


def get_shearlinevar(grb_file, level):
    ds = xr.open_dataset(
        grb_file, filter_by_keys={"typeOfLevel": "isobaricInhPa", "level": level}
    ).sortby("latitude")[["u", "v", "q"]]
    ds = (
        ds.assign_coords(time=ds.valid_time.values)
        .expand_dims("time")
        .drop_vars(["valid_time", "step"])
    )
    return ds


def get_ghtvar(grb_file, level):
    ds = xr.open_dataset(
        grb_file, filter_by_keys={"typeOfLevel": "isobaricInhPa", "level": level}
    ).sortby("latitude")[["gh"]]
    ds = (
        ds.assign_coords(time=ds.valid_time.values)
        .expand_dims("time")
        .drop_vars(["valid_time", "step"])
    )
    return ds


def get_mslpvar(grb_file):
    ds = xr.open_dataset(grb_file, filter_by_keys={"typeOfLevel": "meanSea"}).sortby(
        "latitude"
    )[["prmsl"]]
    ds = (
        ds.assign_coords(time=ds.valid_time.values)
        .expand_dims("time")
        .drop_vars(["valid_time", "step", "meanSea"])
    )
    return ds


def proc(in_dir, out_dir):
    files = sorted(in_dir.glob("*.grb"))

    ds_shrline = []
    target_levels = [1000, 975, 950, 925]
    for lvl in target_levels:
        ds = [
            get_shearlinevar(f, lvl)
            for f in tqdm(files, desc="Getting shearline variable")
        ]
        ds = (
            xr.concat(ds, dim="time")
            .resample(time="3h")
            .mean()
            .rename({"latitude": "lat", "longitude": "lon"})
        )
        ds_shrline.append(ds)
    ds_shrline = xr.concat(ds_shrline, dim="isobaricInhPa")

    ds_ght = []
    target_levels = [1000, 850]
    for lvl in target_levels:
        ds = [
            get_ghtvar(f, lvl) for f in tqdm(files, desc="Getting geopotential height")
        ]
        ds = (
            xr.concat(ds, dim="time")
            .resample(time="3h")
            .mean()
            .rename({"latitude": "lat", "longitude": "lon"})
        )
        ds_ght.append(ds)
    ds_ght = xr.concat(ds_ght, dim="isobaricInhPa")

    ds = [get_mslpvar(f) for f in tqdm(files, desc="Getting mean sea level pressure")]
    ds_mslp = (
        xr.concat(ds, dim="time")
        .resample(time="3h")
        .mean()
        .rename({"latitude": "lat", "longitude": "lon", "prmsl": "mslp"})
    )

    ds = xr.merge([ds_mslp, ds_ght, ds_shrline])

    # --- History append ---
    old = ds.attrs.get("history", "")
    new = (
        "2026-01-19: GFS domain download extended to 100E to 160E, 0N to 30N\n"
        "2026-02-09: Added u, v, q at 1000, 975, 950, 925 hPa to the dataset\n"
        "2026-02-09: Added mslp and gh at 1000 and 850 hPa to the dataset"
    )

    ds.attrs["history"] = old + "\n" + new if old else new

    ts = pd.to_datetime(ds.time.values[0])
    out_file = out_dir / f"gfs_{ts:%Y-%m-%d_%H}_3hrly.nc"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    print("Saving nc...")
    ds.to_netcdf(out_file)
    return ds


if __name__ == "__main__":
    in_dir = Path("dat")
    out_dir = Path("nc")
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hi:o:", ["idir=", "odir="])
    except getopt.GetoptError:
        print("extract_gfs_surfacevar.py -i <input dir> -o <output dir>")
        sys.exit(2)
    for opt, arg in opts:
        if opt == "-h":
            print("extract_gfs_surfacevar.py -i <input dir> -o <output dir>")
            sys.exit()
        elif opt in ("-i", "--idir"):
            in_dir = Path(arg)
        elif opt in ("-o", "--odir"):
            out_dir = Path(arg)
            out_dir.mkdir(parents=True, exist_ok=True)
    proc(in_dir, out_dir)
