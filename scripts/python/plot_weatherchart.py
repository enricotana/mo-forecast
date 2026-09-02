import xarray as xr
import pandas as pd
import numpy as np
from pathlib import Path

from scipy.ndimage import gaussian_filter
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

from scipy.ndimage import gaussian_filter1d, median_filter
import metpy.calc as mpcalc
from math import radians, sin, cos, sqrt, atan2

from scipy.ndimage.filters import maximum_filter, minimum_filter

import getopt
import sys


def plot_maxmin_points(
    ax,
    lon,
    lat,
    data,
    extrema,
    nsize,
    symbol,
    color="k",
    plotValue=True,
    transform=ccrs.PlateCarree(),
):
    """
    Plot relative max/min points (H/L) on a Cartopy map.
    lon, lat : 1D or 2D arrays
    data     : 2D field
    extrema  : 'max' or 'min'
    nsize    : neighborhood size
    """

    if extrema == "max":
        data_ext = maximum_filter(data, nsize, mode="nearest")
    elif extrema == "min":
        data_ext = minimum_filter(data, nsize, mode="nearest")
    else:
        raise ValueError("extrema must be 'max' or 'min'")

    y, x = np.where(data == data_ext)

    for i in range(len(x)):
        lon_pt = lon[x[i]]
        lat_pt = lat[y[i]]

        ax.text(
            lon_pt,
            lat_pt,
            symbol,
            color=color,
            fontsize=24,
            fontweight="bold",
            ha="center",
            va="center",
            transform=transform,
            clip_on=True,
        )

        if plotValue:
            ax.text(
                lon_pt,
                lat_pt,
                f"\n{int(data[y[i], x[i]])}",
                color=color,
                fontsize=12,
                ha="center",
                va="top",
                transform=transform,
                clip_on=True,
            )


def get_vimfc(ds):
    # Define target pressure levels in hPa
    target_levels = [1000, 975, 950, 925]

    U = (
        ds["u"]
        .sel(isobaricInhPa=target_levels)
        .sortby("isobaricInhPa", ascending=False)
    )
    V = (
        ds["v"]
        .sel(isobaricInhPa=target_levels)
        .sortby("isobaricInhPa", ascending=False)
    )
    Q = (
        ds["q"]
        .sel(isobaricInhPa=target_levels)
        .sortby("isobaricInhPa", ascending=False)
    )

    # Compute moisture flux components
    uq = U * Q
    vq = V * Q

    plev = uq.isobaricInhPa.values * 100  # Convert hPa to Pa
    if plev[0] > plev[-1]:  # Check if decreasing
        plev = plev[::-1]  # Reverse to increasing

    duq_dx = np.gradient(uq, axis=-1) / 111000  # axis -1 = lon
    dvq_dy = np.gradient(vq, axis=-2) / 111000  # axis -2 = lat

    MFD = duq_dx + dvq_dy  # moisture flux divergence
    g = 9.80665  # gravity [m/s²]
    vimfc_vals = -1 * (1 / g) * np.trapz(MFD, x=plev, axis=0)

    # Create DataArray for the final result
    lat = uq.lat
    lon = uq.lon

    vimfc = xr.DataArray(vimfc_vals, coords=[lat, lon], dims=["lat", "lon"])
    vimfc.name = "VIMFC"
    vimfc.attrs["units"] = "kg m-2 s-1 × 10⁻⁴"
    vimfc.attrs["long_name"] = (
        "Vertically Integrated Moisture Flux Convergence (1000–925 hPa)"
    )

    # Remove problematic edges (crop 1 grid point on each side)
    vimfc_ds = vimfc.isel(lat=slice(1, -1), lon=slice(1, -1))
    return vimfc_ds


def is_close_to_contour(lon, lat, contour_points, threshold_km=555):
    for cl_lon, cl_lat in contour_points:
        dist = haversine_distance_km(lat, lon, cl_lat, cl_lon)
        if dist <= threshold_km:
            return True
    return False


def haversine_distance_km(lat1, lon1, lat2, lon2):
    R = 6371.0  # Earth's radius in kilometers
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = (
        sin(dlat / 2) ** 2
        + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    )
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c


def cluster_by_haversine(points, threshold_km=50):
    clusters = []
    for lon, lat in points:
        added = False
        for cluster in clusters:
            for cl_lon, cl_lat in cluster:
                dist = haversine_distance_km(lat, lon, cl_lat, cl_lon)
                if dist < threshold_km:
                    cluster.append((lon, lat))
                    added = True
                    break
            if added:
                break
        if not added:
            clusters.append([(lon, lat)])
    return clusters


def shearline_detection(ds_hr, vimfc_ds):
    u_925 = ds_hr["u"].sel(isobaricInhPa=925).sel(lon=slice(115, 160), lat=slice(5, 30))
    v_925 = ds_hr["v"].sel(isobaricInhPa=925).sel(lon=slice(115, 160), lat=slice(5, 30))

    RV_925 = mpcalc.vorticity(u_925, v_925)

    # lon_values = v_925["lon"].values
    lat_values = v_925["lat"].values

    R = 6.371e6  # Earth radius in meters
    dy = np.deg2rad(np.mean(np.diff(lat_values))) * R
    print("dy (m):", dy)

    vimfc_subset = vimfc_ds.sel(lon=slice(115, 160), lat=slice(5, 30))
    # V = v_925 * units("m/s")

    lats = v_925.lat.values
    lons = v_925.lon.values
    dV_dy = mpcalc.geospatial_gradient(v_925, return_only="df/dy").magnitude

    cs2 = plt.contour(lons, lats, v_925.values, levels=[0])
    contour_points = []
    for c in cs2.collections[0].get_paths():
        v = c.vertices
        for x, y in v:
            contour_points.append((x, y))  # ✅ correct indentation
    plt.close()

    shear_points = []
    # Make sure all datasets use the same lat and lon slices
    lats_common = np.intersect1d(v_925.lat, vimfc_subset.lat)
    lons_common = np.intersect1d(v_925.lon, vimfc_subset.lon)

    # u_925_sub = u_925.sel(lat=lats_common, lon=lons_common)
    v_925_sub = v_925.sel(lat=lats_common, lon=lons_common)
    RV_925_sub = RV_925.sel(lat=lats_common, lon=lons_common)
    vimfc_sub = vimfc_subset.sel(lat=lats_common, lon=lons_common)

    # V = v_925_sub * units("m/s")
    dV_dy = mpcalc.geospatial_gradient(v_925_sub, return_only="df/dy").magnitude

    # Now all arrays have the same shape along lat/lon

    shear_points = []
    for i, lon in enumerate(lons_common):
        valid_mask = (
            (dV_dy[:, i] <= -1e-5)
            & (vimfc_sub.values[:, i] > 0)
            & (RV_925_sub.values[:, i] > 0)
        )
        shear_lats = lats_common[valid_mask]
        for lat in shear_lats:
            if is_close_to_contour(lon, lat, contour_points, threshold_km=555):
                shear_points.append([lon, lat])

    rounded_shear_points = np.round(shear_points, 2)
    unique_shear_points = np.unique(rounded_shear_points, axis=0)

    # Print number of points before and after filtering duplicates
    # print(f"Original number of points: {len(shear_points)}")
    # print(f"Number of unique points after rounding: {len(unique_shear_points)}")

    # Apply the clustering
    clusters = cluster_by_haversine(unique_shear_points, threshold_km=50)
    shear_points = np.array(unique_shear_points)

    # Assign labels manually
    labels = np.full(len(shear_points), -1)
    label_counter = 0
    for cluster in clusters:
        for pt in cluster:
            idx = np.where(
                (shear_points[:, 0] == pt[0]) & (shear_points[:, 1] == pt[1])
            )[0]
            labels[idx] = label_counter
        label_counter += 1

    # Group clustered points into separate shear lines
    clustered_shear_lines = {}
    for i, label in enumerate(labels):
        if label == -1:
            continue  # Ignore noise points
        if label not in clustered_shear_lines:
            clustered_shear_lines[label] = []
        clustered_shear_lines[label].append(shear_points[i])

    # Apply smoothing and interpolation
    smoothed_shear_lines = {}
    for label, points in clustered_shear_lines.items():
        points = np.array(points)

        points = points[np.argsort(points[:, 1])]  # Sort by longitude

        lons = points[:, 1]  # Longitude
        lats = points[:, 0]  # Latitude

        # Check if the longitude span is at least 5 degrees
        if lons.max() - lons.min() < 10:
            continue  # Skip shear lines with longitude length < 5 degrees

        # Apply smoothing filters
        median_lat = median_filter(lats, size=4)
        smoothed_lat = gaussian_filter1d(median_lat, sigma=40)

        # Store the smoothed shear lines
        smoothed_shear_lines[label] = (lons, smoothed_lat)

    # Print the number of retained clusters
    print(f"Number of clusters retained: {len(smoothed_shear_lines)}")

    print("\nNumber of points in each cluster after smoothing:")
    for label, (lons, lats) in smoothed_shear_lines.items():
        num_points = len(lons)
        print(f"Cluster {label}: {num_points} points")

    return smoothed_shear_lines


def save_shearline_csv(ds, out_dir):
    shearline_df = pd.DataFrame(columns=np.arange(0, 1500, 1))
    for hour in ds.time.to_numpy()[1:]:
        hour_datetime = (
            (ds.sel(time=hour).time + pd.Timedelta(hours=8)).dt.strftime("%d %H").item()
        )

        ds_hr = ds.sel(time=hour, drop=True)
        vimfc_ds = get_vimfc(ds_hr)
        smoothed_shear_lines = shearline_detection(ds_hr, vimfc_ds)
        if len(smoothed_shear_lines) == 0:
            pass
        else:
            for i, label in enumerate(list(smoothed_shear_lines.keys())):
                smoothed_shear_lon = np.full(1500, np.nan)
                smoothed_shear_lat = np.full(1500, np.nan)
                smoothed_shear_lon[: len(smoothed_shear_lines[label][1])] = (
                    smoothed_shear_lines[label][1]
                )
                smoothed_shear_lat[: len(smoothed_shear_lines[label][0])] = (
                    smoothed_shear_lines[label][0]
                )

                new_row = (
                    pd.DataFrame(
                        {
                            "index": np.arange(0, 1500, 1),
                            f"{hour_datetime}_{i}_lon": smoothed_shear_lon,
                            f"{hour_datetime}_{i}_lat": smoothed_shear_lat,
                        }
                    )
                    .set_index("index")
                    .T
                )
                shearline_df = pd.concat([shearline_df, new_row], ignore_index=False)

    ts = pd.to_datetime(ds.time.values[0]) + np.timedelta64(8, "h")
    out_file = out_dir / f"shearline_{ts:%Y-%m-%d_%H}PHT.csv"
    out_file.parent.mkdir(parents=True, exist_ok=True)

    print("Saving shearline csv...")
    shearline_df.T.to_csv(out_file)
    return shearline_df.T


def plot_weather_chart(ds, shearline_df, out_dir):
    for hour in range(0, len(ds.time), 1):
        init_datetime = (ds.isel(time=0).time).dt.strftime("%Y-%m-%d %H").item()
        dates_datetime = (ds.isel(time=hour).time).dt.strftime("%Y-%m-%d %H").item()

        ds_hr = ds.isel(time=hour, drop=True)
        ght_850 = ds_hr["gh"].sel(isobaricInhPa=850)
        ght_1000 = ds_hr["gh"].sel(isobaricInhPa=1000)
        thickness_1000_850 = gaussian_filter(ght_850 - ght_1000, sigma=3.0)
        mslp = gaussian_filter(ds_hr["mslp"], sigma=3.0) / 100

        map_projection = ccrs.LambertConformal(
            central_longitude=130.0,
            central_latitude=15.0,
            standard_parallels=(33.0, 45.0),
        )

        fs = 22
        fig = plt.figure(1, figsize=(17.0, 11.0))
        ax = plt.subplot(projection=map_projection)
        ax.add_feature(cfeature.COASTLINE, edgecolor="black")
        ax.add_feature(cfeature.LAND, facecolor="lightgray", alpha=0.5)
        ax.add_feature(cfeature.OCEAN, facecolor="#c5e9f9", alpha=0.5)
        ax.set_extent([110, 150, 2, 30], crs=ccrs.PlateCarree())

        ### PLOT SHEARLINE
        print(f"{dates_datetime[-5:]}_0_lat")
        if f"{dates_datetime[-5:]}_0_lon" in shearline_df.columns:
            ax.plot(
                shearline_df[f"{dates_datetime[-5:]}_0_lon"],
                shearline_df[f"{dates_datetime[-5:]}_0_lat"],
                transform=ccrs.PlateCarree(),
                linewidth=10,
                linestyle="-.",
                color="#3D0087",
            )
        else:
            pass

        ### PLOT THICKNESS
        kw_clabels = {
            "fontsize": fs - 2,
            "inline": True,
            "inline_spacing": 2,
            "fmt": "%i",
            "rightside_up": True,
            "use_clabeltext": True,
        }

        th_levels = np.arange(0, 7000, 5)
        th = ax.contour(
            ds_hr.lon,
            ds_hr.lat,
            thickness_1000_850,
            levels=th_levels,
            colors="#025BD7",
            linewidths=1.5,
            linestyles="--",
            transform=ccrs.PlateCarree(),
        )
        plt.clabel(th, **kw_clabels)

        # PLOT MSLP
        clevmslp = np.arange(800.0, 1120.0, 2)
        cs = ax.contour(
            ds_hr.lon,
            ds_hr.lat,
            mslp,
            clevmslp,
            colors="k",
            linewidths=3,
            linestyles="solid",
            transform=ccrs.PlateCarree(),
        )
        plt.clabel(cs, **kw_clabels)
        # Use definition to plot H/L symbols
        plot_maxmin_points(
            ax,
            ds_hr.lon[25:-25],
            ds_hr.lat[25:-25],
            mslp[25:-25, 25:-25],
            "max",
            50,
            symbol="H",
            color="b",
        )
        plot_maxmin_points(
            ax,
            ds_hr.lon[25:-25],
            ds_hr.lat[25:-25],
            mslp[25:-25, 25:-25],
            "min",
            30,
            symbol="L",
            color="r",
        )

        ax.text(
            143.8,
            2.6,
            f"{dates_datetime} LST\nSurface Analysis\nGFS INIT {init_datetime} LST",
            fontweight="bold",
            backgroundcolor="w",
            fontsize=fs,
            horizontalalignment="center",
            verticalalignment="center",
            bbox=dict(facecolor="white", alpha=1.0, edgecolor="black"),
            transform=ccrs.PlateCarree(),
        )

        legend_lines = [
            Line2D([0], [0], color="k", lw=3, label="MSLP (hPa)"),
            Line2D([0], [0], color="#025BD7", lw=3, ls="--", label="1000–850 hPa TH"),
            Line2D([0], [0], color="#3D0087", lw=4, ls="-.", label="Shearline"),
        ]

        fig.legend(
            ncol=3,
            handles=legend_lines,
            fontsize=fs,
            bbox_to_anchor=(0.61, 1.07),
        )
        plt.tight_layout(pad=0.5)

        ts = pd.to_datetime(ds.time.values[0])
        file_prfx = "gfs"
        out_file = (
            out_dir / f"{file_prfx}-{hour*3}hr_weatherchart_{ts:%Y-%m-%d_%H}PHT.png"
        )
        fig.savefig(out_file, bbox_inches="tight", dpi=200)

        plt.close("all")


def proc(in_dir, out_dir):
    ds_og = xr.open_dataset(in_dir)
    init_dt = pd.to_datetime(ds_og.time.values[0])
    init_dt_str = f"{init_dt:%Y%m%d}"
    init_dt_str_hh = f"{init_dt:%H}"

    _out_dir = out_dir / "shearline/csv"
    _out_dir.mkdir(parents=True, exist_ok=True)
    print("Detecting shearline...")
    shearline_df = save_shearline_csv(ds_og, _out_dir)

    _out_dir = out_dir / f"maps/3hrly/{init_dt_str}/{init_dt_str_hh}"
    _out_dir.mkdir(parents=True, exist_ok=True)
    print("Plotting weather chart...")
    ds = ds_og.assign(time=ds_og.time + np.timedelta64(8, "h"))
    plot_weather_chart(ds, shearline_df, _out_dir)


if __name__ == "__main__":
    in_dir = ""
    out_dir = ""
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hi:o:", ["ifile=", "odir="])
    except getopt.GetoptError:
        print("plot_weatherchart.py -i <in_dir file> -o <output dir>")
        sys.exit(2)
    for opt, arg in opts:
        if opt == "-h":
            print("plot_weatherchart.py -i <in_dir file> -o <output dir>")
            sys.exit()
        elif opt in ("-i", "--ifile"):
            in_dir = arg
        elif opt in ("-o", "--odir"):
            out_dir = Path(arg)
            out_dir.mkdir(parents=True, exist_ok=True)

    proc(in_dir, out_dir)
