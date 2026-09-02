#!/bin/bash
# Note: to run, declare GSMAP_DATA if 'gauge', 'nrt', or 'now', e.g.
# $ export GSMAP_DATA='gauge'

echo "------------------"
echo " Downloading latest GSMaP files... "
echo "------------------"

# choose which data type to download
DATA=${GSMAP_DATA}

# Set variables
DL_LIST=$TEMP_DIR/gsmap_dl_list.txt
DL_OUT=$TEMP_DIR/gsmap_dl.out
DL_LOG_DIR="$LOG_DIR/input/gsmap"
DL_SPEED_LOG_FILE="${DL_LOG_DIR}/gsmap_dl_speed_${FCST_YY_GSMAP}${FCST_MM_GSMAP}.log"

mkdir -p "$TEMP_DIR"
mkdir -p "$DL_LOG_DIR"

# get start and end of window hours
SDATE=$(date -d "${FCST_YY_GSMAP}-${FCST_MM_GSMAP}-${FCST_DD_GSMAP} ${FCST_ZZ_GSMAP}:00:00 " +'%Y-%m-%d %H:%M:%S')
EDATE=$(date -d "${FCST_YY_GSMAP}-${FCST_MM_GSMAP}-${FCST_DD_GSMAP} ${FCST_ZZ_GSMAP}:00:00 24 hours" +'%Y-%m-%d %H:%M:%S')

# URL Download GSMaP via FTP site
GAUGE_DIR=ftp://rainmap:Niskur+1404@hokusai.eorc.jaxa.jp/realtime_ver/v8/hourly_G
NRT_DIR=ftp://rainmap:Niskur+1404@hokusai.eorc.jaxa.jp/realtime_ver/v8/archive
NOW_DIR=ftp://rainmap:Niskur+1404@hokusai.eorc.jaxa.jp/now/latest
if [ "$DATA" = 'gauge' ]; then
  FTP_DIR=$GAUGE_DIR
elif [ "$DATA" = 'nrt' ]; then
  FTP_DIR=$NRT_DIR
else
  FTP_DIR=$NOW_DIR
fi

# Create download list
touch "$DL_LIST"

CDATE=$SDATE
while [ "$CDATE" != "$EDATE" ]; do
  YY2=${CDATE:0:4}
  MM2=${CDATE:5:2}
  DD2=${CDATE:8:2}
  HH2=${CDATE:11:2}
  DIR_SOURCE="$YY2/$MM2/$DD2"
  if [ "$DATA" = "now" ]; then
    FILE_NAME="gsmap_${DATA}.${YY2}${MM2}${DD2}.${HH2}00_${HH2}59.dat.gz"
    URL="${FTP_DIR}/${FILE_NAME}"
  else
    FILE_NAME="gsmap_${DATA}.${YY2}${MM2}${DD2}.${HH2}00.dat.gz"
    URL="${FTP_DIR}/${DIR_SOURCE}/${FILE_NAME}"
  fi
  echo "${URL}" >>"$DL_LIST"
  echo -e "\tdir=$GSMAP_TEMP_DIR" >>"$DL_LIST"
  CDATE=$(date -d "$CDATE 1 hour" +'%Y-%m-%d %H:%M:%S')
done

# Wait for files to be available at certain time of day
CDATE=$(date -d "$CDATE 12 hour" +%s)
while [ "$(date +%s)" -lt "$CDATE" ]; do
  echo "waiting for gsmap files to be available"
  sleep 10m
done

DATE_STR=$(date +"%Y%m%d,%H")
# Record start time
DL_STIME=$(date +%s)

# Download
DL_LOG="${DL_LOG_DIR}/gsmap_dload_${FCST_YYYYMMDD_GSMAP}${FCST_ZZ_GSMAP}.log"
aria2c -j5 -x8 -i "$DL_LIST" -l "$DL_LOG" --log-level=notice

# Record end time
DL_ETIME=$(date +%s)
# Compute elapsed time in seconds
DL_DURATION=$((DL_ETIME - DL_STIME))
# Get total download size
TOT_SIZE=$(du -sk "$GSMAP_TEMP_DIR/dat" | cut -f1)
# Compute download speed
DL_SPEED=$(bc <<<"scale=2; ${TOT_SIZE}/${DL_DURATION}")
# Log Speed
echo "${DATE_STR},${DL_DURATION},${TOT_SIZE},${DL_SPEED}" >>"$DL_SPEED_LOG_FILE"

# Cleanup
rm -f "$DL_LIST"
rm -f "$DL_OUT"

echo "-----------------------------------"
echo " Finished downloading gsmap files! "
echo "-----------------------------------"
