#!/usr/bin/env bash

#################### CONSTANTS ####################
DOWNLOAD_INPUT=1
DOWNLOAD_MADIS=1
UPLOAD_OUTPUT=1
POST_PROCESS=1
SLURM_OPTS0=("--parsable" "-A" "$SLURM_ACCOUNT" "-p" "$SLURM_PARTITION" "-N" "$SLURM_NUM_NODES")
###################################################

#################### FUNCTIONS ####################
function show_usage() {
  printf "Usage: %s [options [parameters]]\n" "$0"
  printf "\n"
  printf "Options:\n"
  printf " --no-download, Do not download WRF inputs (GFS, etc...)\n"
  printf " --no-download-madis, Do not download 3DVAR inputs (MADIS, etc...)\n"
  printf " --no-upload, Do not upload outputs\n"
  printf " --no-post-proc, No post processing\n"
  printf " -h|--help, Print help\n"

  return 0
}
###################################################

################### PROCESS ARGS ###################
while [ -n "$1" ]; do
  case "$1" in
  --no-download)
    DOWNLOAD_INPUT=0
    ;;
  --no-download-madis)
    DOWNLOAD_MADIS=0
    ;;
  --no-upload)
    UPLOAD_OUTPUT=0
    ;;
  --no-post-proc)
    POST_PROCESS=0
    ;;
  *)
    show_usage
    ;;
  esac
  shift
done
###################################################

# Cancel any jobs from previous cycle
job_list=$(squeue -u "$SLURM_USER" -p "$SLURM_PARTITION" --format="%i %j" | grep ecw | awk '{print $1}')
if [ -n "$job_list" ]; then

  for j in $job_list; do
    jobs+=("$j")
  done

  scancel "${jobs[@]}"
fi

echo "-----------------------"
echo " Starting WRF Forecast "
echo "-----------------------"

source "$SCRIPT_DIR/set_date_vars.sh"
SCRIPTS_LOG_DIR="$LOG_DIR/scripts"
MODEL_LOG_DIR="$LOG_DIR/model"
POST_LOG_DIR="$LOG_DIR/post"
export ERROR_FILE=$TEMP_DIR/error.txt

mkdir -p "$MODEL_LOG_DIR"
mkdir -p "$POST_LOG_DIR"
rm -f "$ERROR_FILE"

if [ $DOWNLOAD_INPUT -eq 1 ]; then
  # download GFS
  source "$SCRIPT_DIR/download_gfs.sh"
fi

if [[ $WRF_MODE == '3dvar' && $DOWNLOAD_MADIS -eq 1 ]]; then
  # download MADIS
  source "$SCRIPT_DIR/download_madis.sh"
fi

NUM_TIMESTEPS=$((WRF_FCST_DAYS * 24 + 1))
GFS_FILES=("$GFS_DIR"/*.grb)

# Redownload GFS files if incomplete
if [ ${#GFS_FILES[@]} -ne $NUM_TIMESTEPS ]; then
  echo "GFS files incomplete, redownloading.."
  sleep 5m # allowance in case of internet disconnection/server overload
  source "$SCRIPT_DIR/download_gfs.sh"
fi

# Send notifier if GFS files still incomplete
GFS_FILES=("$GFS_DIR"/*.grb)
if [ ${#GFS_FILES[@]} -ne $NUM_TIMESTEPS ]; then
  err_msg="number of GFS Files: ${#GFS_FILES[@]}, expected: $NUM_TIMESTEPS"
  echo "$err_msg" >"$ERROR_FILE"
  source "$SCRIPT_DIR/send_alert.sh"
  echo "$err_msg"
  exit 1
fi

# Weather Chart
mkdir -p "$SCRIPTS_LOG_DIR"
wc_log_file="$SCRIPTS_LOG_DIR/weatherchart_$FCST_YYYYMMDD$FCST_ZZ.out"
slurm_opts=("${SLURM_OPTS0[@]}")
slurm_opts+=("-J" "ecw_wc-$FCST_YYYYMMDD$FCST_ZZ")
slurm_opts+=("-o" "$wc_log_file")
slurm_opts+=("-n" "2")
slurm_opts+=("$SCRIPT_DIR/run_weatherchart.sh")
prev_jid=$(sbatch "${slurm_opts[@]}")

# WPS
mkdir -p "$MODEL_LOG_DIR/wps"
wps_log_file="$MODEL_LOG_DIR/wps/wps_$FCST_YYYYMMDD$FCST_ZZ.out"
slurm_opts=("${SLURM_OPTS0[@]}")
slurm_opts+=("-J" "ecw_wps-$FCST_YYYYMMDD$FCST_ZZ")
slurm_opts+=("-o" "$wps_log_file")
slurm_opts+=("-n" "$SLURM_WPS_NTASKS")
slurm_opts+=("$SCRIPT_DIR/run_wps.sh")
prev_jid=$(sbatch "${slurm_opts[@]}")

# WRF
# schedule multiple slurm WRF jobs based on WRF_RUN_NAMES
IFS=':' read -ra run_names <<<"$WRF_RUN_NAMES"
IFS=':' read -ra run3dvar_names <<<"$WRFDA_RUN_NAMES"
run_idx=1
for run_name in "${run_names[@]}"; do
  export NAMELIST_RUN=$run_name

  if [[ $WRF_MODE == '3dvar' ]]; then
    export NAMELIST_3DVar=${run3dvar_names[$run_idx - 1]}
  fi

  WRF_NTASKS=$SLURM_WRF_NTASKS
  mkdir -p "$MODEL_LOG_DIR/wrf"
  wrf_log_file="$MODEL_LOG_DIR/wrf/wrf_$FCST_YYYYMMDD${FCST_ZZ}_run${run_idx}.out"
  slurm_opts=("${SLURM_OPTS0[@]}")
  slurm_opts+=("-d" "afterany:$prev_jid")
  slurm_opts+=("-J" "ecw_wrf-$FCST_YYYYMMDD${FCST_ZZ}_run${run_idx}")
  slurm_opts+=("-o" "$wrf_log_file")
  slurm_opts+=("-n" "$WRF_NTASKS")
  slurm_opts+=("-c" "$SLURM_WRF_CPUS_PER_TASK")
  slurm_opts+=("$SCRIPT_DIR/run_wrf.sh")
  prev_jid=$(sbatch "${slurm_opts[@]}")

  run_idx=$((run_idx + 1))
done

if [ $POST_PROCESS -eq 1 ]; then
  # Post processing

  ### Python Post processing
  log_file="$POST_LOG_DIR/python_$FCST_YYYYMMDD${FCST_ZZ}_run${run_idx}.log"
  slurm_opts=("${SLURM_OPTS0[@]}")
  slurm_opts+=("-d" "afterany:$prev_jid")
  slurm_opts+=("-J" "ecw_python-$FCST_YYYYMMDD$FCST_ZZ")
  slurm_opts+=("-o" "$log_file")
  slurm_opts+=("-n" "12")
  slurm_opts+=("$SCRIPT_DIR/postproc_python.sh")
  prev_jid=$(sbatch "${slurm_opts[@]}")

  if [ $UPLOAD_OUTPUT -eq 1 ]; then
    ### Web Upload
    mkdir -p "$POST_LOG_DIR/upload"
    log_file="$POST_LOG_DIR/upload/web-upload_$FCST_YYYYMMDD$FCST_ZZ.log"
    slurm_opts=("${SLURM_OPTS0[@]}")
    slurm_opts+=("-d" "afterany:$prev_jid")
    slurm_opts+=("-J" "ecw_web-upload-$FCST_YYYYMMDD$FCST_ZZ")
    slurm_opts+=("-o" "$log_file")
    slurm_opts+=("-n" "1")
    slurm_opts+=("$SCRIPT_DIR/web_upload.sh")
    prev_jid=$(sbatch "${slurm_opts[@]}")
  fi
fi

### EWB Quicklook plots
mkdir -p "$POST_LOG_DIR/ewb"
log_file="$POST_LOG_DIR/ewb/ewb_$FCST_YYYYMMDD$FCST_ZZ.log"
slurm_opts=("${SLURM_OPTS0[@]}")
slurm_opts+=("-d" "afterany:$prev_jid")
slurm_opts+=("-J" "ecw_ewb-$FCST_YYYYMMDD$FCST_ZZ")
slurm_opts+=("-o" "$log_file")
slurm_opts+=("-n" "1")
slurm_opts+=("$EWB_DIR/run_ewb_quicklook.sh")
prev_jid=$(sbatch "${slurm_opts[@]}")


### ECW-validation for extreme rainfall only
mkdir -p "$POST_LOG_DIR/validation"
log_file="$POST_LOG_DIR/validation/valdn_ari_$FCST_YYYYMMDD$FCST_ZZ.log"
slurm_opts=("${SLURM_OPTS0[@]}")
slurm_opts+=("-d" "afterany:$prev_jid")
slurm_opts+=("-J" "ecw_valdn-$FCST_YYYYMMDD$FCST_ZZ")
slurm_opts+=("-o" "$log_file")
slurm_opts+=("-n" "1")
slurm_opts+=("$VALID_DIR/run_rain_extreme_verification.sh")
prev_jid=$(sbatch "${slurm_opts[@]}")


### For WRF Anomaly every 1st day of the month and for Arowana only
date=$(date +"%d")
hostname=$(hostname -s)
### check date if 1st day of the month
if [ $date == 01 ] && [ $hostname == "arowana" ]; then
    echo "Calculating Anomalies"  ### Anomaly plots

    mkdir -p "$POST_LOG_DIR/anomaly"
    log_file="$POST_LOG_DIR/anomaly/anom_$FCST_YYYYMMDD.log"
    slurm_opts=("${SLURM_OPTS0[@]}")
    slurm_opts+=("-d" "afterany:$prev_jid")
    slurm_opts+=("-J" "anom-$FCST_YYYYMMDD")
    slurm_opts+=("-o" "$log_file")
    slurm_opts+=("-n" "1")
    slurm_opts+=("$SCRIPT_DIR/run_anomaly.sh")
    prev_jid=$(sbatch "${slurm_opts[@]}")

else
    echo "nothing to run"  ### Nothing to run
fi

### Notifier
mkdir -p "$POST_LOG_DIR/alert"
log_file="$POST_LOG_DIR/alert/alert_$FCST_YYYYMMDD$FCST_ZZ.log"
slurm_opts=("${SLURM_OPTS0[@]}")
slurm_opts+=("-d" "afterany:$prev_jid")
slurm_opts+=("-J" "ecw_alert-$FCST_YYYYMMDD$FCST_ZZ")
slurm_opts+=("-o" "$log_file")
slurm_opts+=("-n" "1")
slurm_opts+=("$SCRIPT_DIR/send_alert.sh")
prev_jid=$(sbatch "${slurm_opts[@]}")
