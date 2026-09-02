from cartopy import crs as ccrs
from cartopy.mpl.ticker import LongitudeFormatter, LatitudeFormatter
import matplotlib as mp

import numpy as np

mp.rcParams["font.size"] = 9

plot_proj = ccrs.PlateCarree()


def plot_format(ax):
    lon_formatter = LongitudeFormatter(zero_direction_label=True, degree_symbol="")
    lat_formatter = LatitudeFormatter(degree_symbol="")

    lon_labels = range(120, 130, 5)
    lat_labels = range(5, 25, 5)
    xlim = (116, 128)
    ylim = (5, 20)

    ax.xaxis.set_major_formatter(lon_formatter)
    ax.yaxis.set_major_formatter(lat_formatter)
    ax.set_xticks(lon_labels, crs=plot_proj)
    ax.set_yticks(lat_labels, crs=plot_proj)
    ax.coastlines()
    ax.set_extent((*xlim, *ylim))

    ax.annotate(
        "observatory.ph",
        xy=(10, 10),
        xycoords="axes points",
        fontsize=7,
        bbox=dict(boxstyle="square,pad=0.3", alpha=0.5),
        alpha=0.65,
    )
    return ax


def plot_footer(ax, var):
    footer = "1971-2000 APHRODITE" if var == "temp" else "2001-2020 GSMaP"
    ax.text(
        x=116,
        y=3.5,
        s=f"*baseline: {footer}",
        fontsize=7,
    )
    return ax


plot_vars = {
    "rain_actual": {
        "title": "Total Rainfall\n(WRF ensemble)",
        "units": "mm",
        "levels": np.arange(50, 500, 50),
        "colors": [
            "#ffffff",
            "#0064ff",
            "#01b4ff",
            "#32db80",
            "#9beb4a",
            "#ffeb00",
            "#ffb302",
            "#ff6400",
            "#eb1e00",
            "#af0000",
        ],
    },
    "rain_monthly": {
        "units": "mm",
        "levels": np.arange(50, 650, 50),
        "colors": [
            "#d6d6d6",  # 0. Light desaturated brown
            "#bdc9b7",  # 1. Earthy olive-grey green
            "#c8e6b4",  # 2. Pale green
            "#a8dba3",  # 3. Light green
            "#8cd790",  # 4. Fresh light green
            "#6fc47c",  # 5. Light-medium green
            "#56b870",  # 6. Mid green
            "#3da85f",  # 7. Moderate green
            "#2d9950",  # 8. Leafy green
            "#1f9d80",  # 9. Green-teal
            "#1aa88f",  # 10. Soft teal
            "#16b39c",  # 11. Medium teal
            "#11beb0",  # 12. Seafoam teal
            "#0ccac4",  # 13. Aqua teal
            "#1ebfdc",  # 14. Light blue
            "#2aa7e5",  # 15. Mid blue
            "#368eea",  # 16. Moderate blue
            "#3d75e3",  # 17. Deep blue
            "#385fd0",  # 18. Dark blue
            "#2f49aa",  # 19. Very wet/extreme
        ],
    },
    "rain_anomaly": {
        "title": "Total Rainfall Anomaly\n(WRF ensemble minus baseline*)",
        "units": "mm",
        "levels": np.arange(-150, 175, 25),
        "colors": [
            mp.colors.rgb2hex(mp.cm.get_cmap("BrBG")(i))
            for i in range(mp.cm.get_cmap("BrBG").N)
        ],
    },
    "rain_difference": {
        "units": "%",
        "levels": np.arange(-220, 260, 40),
        "colors": [
            mp.colors.rgb2hex(mp.cm.get_cmap("BrBG")(i))
            for i in range(mp.cm.get_cmap("BrBG").N)
        ],
    },
    "temp_actual": {
        "title": "Average Temperature\n(WRF ensemble)",
        "units": "°C",
        "levels": np.arange(18, 34, 2),
        "colors": [
            mp.colors.rgb2hex(mp.cm.get_cmap("YlOrRd")(i))
            for i in range(mp.cm.get_cmap("YlOrRd").N)
        ],
    },
    "temp_monthly": {
        "units": "°C",
        "levels": np.arange(16, 32, 2),
        "colors": [
            mp.colors.rgb2hex(mp.cm.get_cmap("YlOrRd")(i))
            for i in range(mp.cm.get_cmap("YlOrRd").N)
        ],
    },
    "temp_anomaly": {
        "title": "Average Temperature\n(WRF ensemble minus baseline*)",
        "units": "°C",
        "levels": np.arange(-2.5, 3.0, 0.5),
        "colors": [
            mp.colors.rgb2hex(mp.cm.get_cmap("coolwarm")(i))
            for i in range(mp.cm.get_cmap("coolwarm").N)
        ],
    },
    "temp_difference": {
        "units": "°C",
        "levels": np.arange(-1.5, 1.8, 0.3),
        "colors": [
            mp.colors.rgb2hex(mp.cm.get_cmap("bwr")(i))
            for i in range(mp.cm.get_cmap("bwr").N)
        ],
    },
}
