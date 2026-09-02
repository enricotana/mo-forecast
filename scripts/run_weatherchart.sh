#!/bin/bash


cd "$SCRIPT_DIR/python" || exit

echo "---------------------------------"
echo "  Getting GFS surface variables  "
echo "---------------------------------"

# Extract GFS variables needed for plotting
$PYTHON extract_gfs_surfacevar.py -i "$GFS_DIR" -o "$GFS_NC_DIR"

echo "---------------------------------"
echo " Start plotting weather charts!  "
echo "---------------------------------"

# Plot surface weather charts with shearline
GFS_OUT_FILE="${GFS_NC_DIR}/gfs_${FCST_YY}-${FCST_MM}-${FCST_DD}_${FCST_ZZ}_3hrly.nc"
$PYTHON plot_weatherchart.py -i "$GFS_OUT_FILE" -o "$OUTDIR"

echo "---------------------------------"
echo "Plotting weather charts finished!"
echo "---------------------------------"

cd "$MAINDIR" || exit