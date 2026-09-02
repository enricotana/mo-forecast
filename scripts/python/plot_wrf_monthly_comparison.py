import pandas as pd
import numpy as np
import xarray as xr
import calendar
import time
from datetime import datetime

import os

import matplotlib as mp
import matplotlib.pyplot as plt

from config import Config
from helpers.anomaly_format import plot_proj, plot_vars, plot_format

conf = Config()
resources_dir = conf.script_dir / "python/resources/nc"
wrf_dir = conf.data_dir / "anomaly/nc"
inp_dir = os.getenv("WRF_SERVER_DIR")
out_dir = conf.data_dir / "anomaly/img/monthly_comparison"


def get_combined_dataset(date):
    try:
        _current_date = pd.to_datetime(date).strftime("%Y-%m")
        _previous_date = (pd.to_datetime(date) - pd.DateOffset(years=1)).strftime(
            "%Y-%m"
        )

        _this_year = xr.open_dataset(f"{wrf_dir}/wrf_anomaly_{_current_date}.nc")[
            ["temp", "rain"]
        ]
        _previous_year = xr.open_dataset(f"{wrf_dir}/wrf_anomaly_{_previous_date}.nc")[
            ["temp", "rain"]
        ]

        combined_data = xr.concat([_this_year, _previous_year], dim="time")

        _mask = xr.open_dataset(f"{resources_dir}/WRF_LANDMASK_PH.nc")
        combined_data = combined_data.where(_mask.LANDMASK == 1)
        combined_data = combined_data.where(combined_data.rain >= 1)
        return combined_data
    except FileNotFoundError:
        print("One or both of the monthly files are missing.")


def plot_comparison():  ## plot anomalies per month
    start = time.time()

    date = pd.to_datetime("today") - pd.DateOffset(months=1)
    print(date)
    dataset = get_combined_dataset(date)

    dates = dataset.time.values

    # Check if plot file already exists
    date = pd.to_datetime(date)
    month_label = date.strftime("%Y-%m")

    dates_list = [dates[0], dates[1], "Difference"]

    titles = {
        "rain": "Total Rainfall (in mm)",
        "temp": "Average Temperature (in °C)",
    }

    for var in ["rain", "temp"]:
        print(f"Plotting {var}....")
        out_file = f"{out_dir}/wrf_{var}_monthly_comparison_{month_label}.png"
        plot_exists = os.path.exists(out_file)

        if plot_exists:
            print("▮▮▮ Files exist, nothing to plot.....")
        else:
            print(f"    Plotting {date}...")
            fsize = 12
            fig, axes = plt.subplots(
                ncols=3,
                figsize=(13, 8),
                subplot_kw={"projection": plot_proj},
                constrained_layout=True,
            )
            for ax, date_index in zip(axes.flatten(), range(len(dates) + 1)):
                if ax != axes.flatten()[-1]:  # For actual values
                    var_info = plot_vars.get(f"{var}_monthly")
                    input_data = dataset.isel(time=date_index, drop=False)
                    # Title Format
                    date_ts = pd.to_datetime(dates_list[date_index])
                    month_int = date_ts.month
                    month_str = calendar.month_name[month_int]
                    year_str = date_ts.year
                    ax_title = f"{month_str} {year_str}"

                else:  # For monthly difference
                    var_info = plot_vars.get(f"{var}_difference")
                    input_data = dataset.isel(time=0) - dataset.isel(time=1)
                    # Makes rain pct difference instead of absolute difference
                    pct_diff = (
                        (dataset.isel(time=0) - dataset.isel(time=1))
                        / dataset.isel(time=1)
                    ) * 100
                    input_data["rain"] = pct_diff["rain"]
                    ax_title = f"{month_str} {year_str+1} minus {month_str} {year_str}"

                levels = var_info["levels"]
                colors = mp.colors.LinearSegmentedColormap.from_list(
                    "", var_info["colors"]
                )
                var_sub = input_data[var]
                p = var_sub.plot.contourf(
                    "lon",
                    "lat",
                    cmap=colors,
                    levels=levels,
                    extend="both",
                    add_labels=False,
                    add_colorbar=False,
                    transform=plot_proj,
                    ax=ax,
                )
                input_data[f"aave_{var}"] = input_data[var].mean(("lat", "lon"))
                aave = input_data[f"aave_{var}"].values.tolist()
                ax.annotate(
                    f"AAVE: {np.round(aave, 2)}",
                    xy=(116.35, 19.2),
                    xycoords="data",
                    fontsize=fsize,
                    bbox=dict(boxstyle="square", fc="white", pad=0.3, alpha=0.5),
                )

                plot_format(ax)
                ax.label_outer()
                ax.set_title(ax_title, fontsize=fsize, y=1.025)
                cbar = plt.colorbar(p, ax=ax, ticks=levels, shrink=0.35)
                cbar.ax.tick_params(labelsize=fsize - 2)
                p.colorbar.ax.set_title(
                    f"[{var_info['units']}]", pad=25, loc="left", fontsize=fsize
                )
            plt_title = f"{titles[var]}\n(WRF ensemble)"
            fig.suptitle(plt_title, fontsize=12, y=0.9)
            plt.savefig(
                out_file,
                dpi=200,
                facecolor="white",
                bbox_inches="tight",
            )
            plt.close()

    end = time.time()
    elapsed = end - start

    print(
        f"▮▮▮ Elapsed time in real time : {datetime.strftime(datetime.utcfromtimestamp(elapsed), '%H:%M:%S')}"
    )


if __name__ == "__main__":
    out_dir.mkdir(parents=True, exist_ok=True)
    plot_comparison()
