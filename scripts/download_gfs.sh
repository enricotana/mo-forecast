#!/usr/bin/env bash

echo "---------------------------------"
echo " Downloading latest GFS files... "
echo "---------------------------------"

# Set variables
DL_LIST=$TEMP_DIR/gfs_dl_list.txt
DL_OUT=$TEMP_DIR/gfs_dl.out
DL_LOG_DIR="$LOG_DIR/input/gfs_files"
DL_SPEED_LOG_FILE="${DL_LOG_DIR}/gfs_dl_speed_${FCST_YY}${FCST_MM}.log"

mkdir -p "$GFS_DIR"
mkdir -p "$TEMP_DIR"
mkdir -p "$DL_LOG_DIR"

END_TS=$((WRF_FCST_DAYS * 24)) # Last timestep to download

# URL
BASE_URL="https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25.pl"
FILE_PARAM="file=gfs.t${FCST_ZZ}z.pgrb2.0p25.f"
DIR_PARAM="dir=/gfs.${FCST_YYYYMMDD}/${FCST_ZZ}/atmos"
STATIC_PARAMS="all_lev=on&all_var=on&subregion=&leftlon=100&rightlon=160&toplat=30&bottomlat=0"
TEST_TS=$(printf "%03d\n" $END_TS)
TEST_FILE_PARAM="file=gfs.t${FCST_ZZ}z.pgrb2.0p25.f$TEST_TS"
TEST_PARAMS="var_RH=on&subregion=&leftlon=115&rightlon=120&toplat=10&bottomlat=5"

# Create download list
touch "$DL_LIST"
for i in $(seq -f "%03g" 0 $END_TS); do
  if [ ! -f "$GFS_DIR/GFS$i.grb" ]; then
    URL="${BASE_URL}?${FILE_PARAM}${i}&${DIR_PARAM}&${STATIC_PARAMS}"
    echo "${URL}" >>"$DL_LIST"
    echo -e "\tout=GFS$i.grb" >>"$DL_LIST"
  fi
done

# Wait for files to be available
TEST_URL="${BASE_URL}?${TEST_FILE_PARAM}&${DIR_PARAM}&${TEST_PARAMS}"
i=0
while [ "$i" -lt 10 ] && ! (curl -o/dev/null -sfI "$TEST_URL"); do
  sleep 10m
  i=$((i + 1))
  echo "waiting for gfs files to be available"
done

# Exit if file still doesn't exist
if ! (curl -o/dev/null -sfI "$TEST_URL"); then
  exit 1
fi

DATE_STR=$(date +"%Y%m%d,%H")
# Record start time
DL_STIME=$(date +%s)

# Download
DL_LOG="${DL_LOG_DIR}/gfs_dload_${FCST_YYYYMMDD}${FCST_ZZ}.log"
aria2c -j5 -x8 -d "$GFS_DIR" -i "$DL_LIST" -l "$DL_LOG" --log-level=notice

# Record end time
DL_ETIME=$(date +%s)
# Compute elapsed time in seconds
DL_DURATION=$((DL_ETIME - DL_STIME))
# Get total download size
TOT_SIZE=$(du -sk "$GFS_DIR"/ | cut -f1)
# Compute download speed
DL_SPEED=$(bc <<<"scale=2; $TOT_SIZE/$DL_DURATION")
# Log Speed
echo "$DATE_STR,$DL_DURATION,$TOT_SIZE,$DL_SPEED" >>"$DL_SPEED_LOG_FILE"

# Cleanup
rm -f "$DL_LIST"
rm -f "$DL_OUT"

cd "$SCRIPT_DIR/python" || exit

# Convert GFS precipitation grb files to .nc
$PYTHON convert_gfs_nc.py -i "$GFS_DIR" -o "$GFS_NC_DIR"

cd "$MAINDIR" || exit

echo "---------------------------------"
echo " Finished downloading GFS files! "
echo "---------------------------------"
