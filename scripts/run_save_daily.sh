#!/bin/bash

echo "---------------------------------"
echo "       Saving Daily Output       "
echo "---------------------------------"

# -------------------------------------------- #
#              Calculating                     #
# -------------------------------------------- #

# source "$SCRIPT_DIR/set_date_vars.sh"
export MPLBACKEND="agg"

cd "$SCRIPT_DIR/python" || exit

$PYTHON save_daily.py

echo "---------------------------------"
echo "   Saved Daily Forecast Output!  "
echo "---------------------------------"
cd "$MAINDIR" || exit