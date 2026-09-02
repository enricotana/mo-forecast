#!/usr/bin/env bash

YY=${FCST_YYYYMMDD:0:4}
mm=${FCST_YYYYMMDD:4:2}
dd=${FCST_YYYYMMDD:6:2}

DATE2=$(date -d "$YY-$mm-$dd $FCST_ZZ:00:00 8 hours" +'%Y-%m-%d %H:%M:%S')
read -r YY2 mm2 dd2 HH2 MM2 SS2 <<<"${DATE2//[-: ]/ }"

echo "--------------------------"
echo " Uploading files for web  "
echo "--------------------------"

SRCDIR=${OUTDIR}

IMGS=("$SRCDIR/maps/24hrly/${FCST_YYYYMMDD}/${FCST_ZZ}"/wrf-*"$YY2-$mm2-${dd2}_${HH2}PHT.png")
if [ ${#IMGS[@]} -eq 1 ]; then
  err_msg="No files to upload"
  echo "$err_msg" >>"$ERROR_FILE"
  echo "$err_msg"
  exit 1
fi

cat <<EOF >"$SRCDIR/info.json"
{
    "year": "$YY2",
    "month": "$mm2", 
    "day": "$dd2", 
    "hour": "$HH2"
}
EOF

remotes=("panahon.alapaap" "panahon.linode")
web_dirs=("websites/panahon-php" "websites/panahon-php")
img_types=("24hrly" "3hrly")

for r in "${!remotes[@]}"; do
  scp "$SRCDIR/info.json" "${remotes[$r]}:${web_dirs[$r]}/resources/model/"

  for img_type in "${img_types[@]}"; do
    local_src="$SRCDIR/maps/${img_type}/${FCST_YYYYMMDD}/${FCST_ZZ}"
    remote_dest="${web_dirs[$r]}/resources/model/img/${img_type}/${FCST_YYYYMMDD}/${FCST_ZZ}"
    ssh "${remotes[$r]}" mkdir -p "${remote_dest}"
    scp "${local_src}"/wrf*"$YY2-$mm2-${dd2}_${HH2}PHT.png" "${remotes[$r]}:${remote_dest}"
    scp "${local_src}"/gfs*"$YY2-$mm2-${dd2}_${HH2}PHT.png" "${remotes[$r]}:${remote_dest}"
  done
  scp "$SRCDIR/timeseries/img"/wrf*"$YY2-$mm2-${dd2}_${HH2}PHT.png" "${remotes[$r]}:${web_dirs[$r]}/resources/model/img/"

  # /ecw
  scp "$SRCDIR/web/maps"/wrf-*"$YY2-$mm2-${dd2}_${HH2}PHT.png" "${remotes[$r]}:${web_dirs[$r]}/resources/model/web_img/"
  scp "$SRCDIR/web/json/forecast_$YY2-$mm2-${dd2}_${HH2}PHT.json" "${remotes[$r]}:${web_dirs[$r]}/resources/model/"
done

echo "-----------------------------"
echo " Done uploading web files!!! "
echo "-----------------------------"

echo "--------------------------"
echo " Uploading files for EHB  "
echo "--------------------------"

rsubdir="ewb:EHB/resources/model/hi_gauge/$YY2$mm2$dd2/$HH2"
rclone copy "$SRCDIR/hi_gauge/img/$YY$mm$dd${FCST_ZZ}" "$rsubdir"

echo "-----------------------------"
echo " Done uploading EHB files!!! "
echo "-----------------------------"

echo "--------------------------"
echo " Uploading files for ACEN  "
echo "--------------------------"

rclone copy "$SRCDIR/acenergy/csv/acenergy_SACASOL_$YY2-$mm2-${dd2}_${HH2}PHT.csv" ecw_acen:/ACEN/csv/
rclone copy "$SRCDIR/acenergy/csv/acenergy_SOLARACE1_$YY2-$mm2-${dd2}_${HH2}PHT.csv" ecw_acen:/ACEN/csv/
rclone copy "$SRCDIR/acenergy/img/acenergy-ts_$YY2-$mm2-${dd2}_${HH2}PHT.png" ecw_acen:/ACEN/img/

echo "-----------------------------"
echo " Done uploading ACEN files!!! "
echo "-----------------------------"
