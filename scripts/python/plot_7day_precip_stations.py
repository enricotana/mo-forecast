# Description: Plot 7-day total precipitation for extreme weather bulletin
# Author: Kevin Henson
# Last edited: July 1, 2022

import matplotlib.pyplot as plt
import datetime as dt
import cartopy.crs as ccrs
import pandas as pd
import numpy as np
from pathlib import Path
import matplotlib.colors as mcolors
import cartopy.io.img_tiles as cimgt

today = dt.date.today()
# today = dt.date(2022, 6, 5) # for testing

# Run only once in a day between 12nn and 5pm along with 2pm fcst
current_time = dt.datetime.now()
time_min = current_time.replace(hour=12, minute=0, second=0, microsecond=0)
time_max = current_time.replace(hour=17, minute=0, second=0, microsecond=0)

if current_time > time_min and current_time < time_max:

    aws_dir = "/home/modelman/forecast/input/aws_files/"
    outdir = Path("/home/modelman/forecast/output/web/maps/ewb/")

    # Intialize dataframe
    aws_cols = ['name', 'timestamp', 'rr', 'lat', 'lon']
    df_aws = pd.DataFrame(columns = aws_cols)

    # Loop through past 7 days
    for day in np.arange(0,7):

        # Set date variable
        dt_var = today - dt.timedelta(int(day))
        dt_var_str = str(dt_var)

        # Read station data
        aws_fn = Path(aws_dir + 'stn_obs_24hr_' + dt_var_str +'_08PHT.csv')
        if aws_fn.exists():
            
            aws_df = pd.read_csv(aws_fn,
                                usecols=aws_cols, na_values="-999.000000")
            df_aws = pd.concat([df_aws,aws_df])

    dt_var = today - dt.timedelta(int(day+1))
    dt_var_str = str(dt_var)

    # Get 7 day total precip
    df_sum = df_aws.groupby(['name'])['rr'].sum()
    df_lat_lon = df_aws.groupby(['name'])[['lat','lon']].first()
    df_sum = pd.concat([df_sum,df_lat_lon],axis=1)

    # Plot
    request = cimgt.GoogleTiles()
    fig, ax = plt.subplots(subplot_kw=dict(projection=request.crs))
    extents = [120.76, 121.33, 14.24, 14.87]
    ax.set_extent(extents)
    ax.add_image(request, 10)

    gl = ax.gridlines(crs=ccrs.PlateCarree(), draw_labels=True,
    linewidth=1, color='gray', alpha=0, linestyle='--')
    gl.top_labels = False
    gl.right_labels = False
    gl.xlabel_style = {'size': 7}
    gl.ylabel_style = {'size': 7}

    lon = df_sum['lon']
    lat = df_sum['lat']
    pr = df_sum['rr']

    clevs = [0, 10, 20, 60, 100,
            200, 300, 400, 500, 600, 700, 1000]
    cmap_data = [(1.0, 1.0, 1.0),
                (0.3137255012989044, 0.8156862854957581, 0.8156862854957581),
                (0.0, 1.0, 1.0),
                (0.0, 0.8784313797950745, 0.501960813999176),
                (0.0, 0.7529411911964417, 0.0),
                (0.501960813999176, 0.8784313797950745, 0.0),
                (1.0, 1.0, 0.0),
                (1.0, 0.6274510025978088, 0.0),
                (1.0, 0.0, 0.0),
                (1.0, 0.125490203499794, 0.501960813999176),
                (0.9411764740943909, 0.250980406999588, 1.0),
                (0.501960813999176, 0.125490203499794, 1.0)]

    cmap = mcolors.ListedColormap(cmap_data, 'precipitation')
    norm = mcolors.BoundaryNorm(clevs, cmap.N)

    cs = ax.scatter(lon,lat,s=20,c=pr,edgecolor='black', linewidth = 0.25, alpha=1, 
                transform=ccrs.PlateCarree(), cmap=cmap, norm=norm,
                )

    cbar_ax = fig.add_axes([0.26, 0.04, 0.5, 0.02])
    cbar=fig.colorbar(cs, cax=cbar_ax,orientation='horizontal',extend='max')

    ax.set_title(f'Total Precipitation (mm) \n{dt_var_str}_08 PHT to {str(today)}_08 PHT')

    outdir.mkdir(parents=True, exist_ok=True)
    out_file = outdir / f'station_7day_totalprecip_latest.png'

    print(f'Saving ewb {out_file}...')

    fig.savefig(out_file, bbox_inches="tight", dpi=300)
    plt.close("all")
