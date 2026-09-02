#!/bin/bash

echo "---------------------------------"
echo "     Starting WRF Anomalies      "
echo "---------------------------------"

# -------------------------------------------- #
#              Calculating                     #
# -------------------------------------------- #

# source "$SCRIPT_DIR/set_date_vars.sh"
export MPLBACKEND="agg"

cd "$SCRIPT_DIR/python" || exit

$PYTHON plot_anomaly_maps.py -w True -o 6
$PYTHON plot_wrf_monthly_comparison.py
echo "---------------------------------"
echo " Calculation and plots finished! "
echo "---------------------------------"
cd "$MAINDIR" || exit