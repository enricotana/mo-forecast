#!/bin/bash
# export FCST_YYYYMMDD="20210818"; export FCST_ZZ="00"; . $HOME/forecast/set_cron_env.sh; . $SCRIPT_DIR/set_date_vars.sh; . /home/modelman/forecast/validation/run_validation.sh
PYTHONCONDA=/home/miniconda3/envs/toolbox/bin/python
CDO=/home/miniconda3/envs/toolbox/bin/cdo
export VAL_DIR=$MAINDIR/validation
#export VAL_OUTDIR=$VAL_DIR/output/${FCST_YY}${FCST_MM}${FCST_DD}/$FCST_ZZ
export VAL_OUTDIR=${OUTDIR}/validation/${FCST_YY}${FCST_MM}${FCST_DD}/$FCST_ZZ
# options : gauge , nrt , now [can only be run at 9:00 PHT sharp]
export GSMAP_DATA="gauge"
export STATION_ID="MOIP"
export STATION_NAME="Manila Observatory"

DATE_STR1=$(date -d "${FCST_YY}-${FCST_MM}-${FCST_DD} $FCST_ZZ:00:00 8 hours" +'%Y-%m-%d_%H')
read FCST_YY_PHT FCST_MM_PHT FCST_DD_PHT FCST_HH_PHT <<< ${DATE_STR1//[-_]/ }
# -------------------------------------------- #
#                 GSMaP                        #
# -------------------------------------------- #


echo "--------------------------"
echo " Processing GSMaP files  "
echo "--------------------------"

cd ${VAL_DIR}/gsmap

rm ${VAL_DIR}/gsmap/dat/gsmap_nrt.${FCST_YY}${FCST_MM}${FCST_DD}*.dat
# Download GSMaP data
./download_gsmap.aria2.sh 

# Convert GSMaP .dat files to .nc
./convert_gsmap_nc.sh

# Plot GSMaP
mkdir -p $VAL_OUTDIR
cd ${VAL_DIR}/grads

# Edit GrADS plotting script

sed -i "1s/.*/date='${DATE_STR1}PHT'/" gsmap_24hr_rain.gs
sed -i "2s/.*/date2='${DATE_STR1} PHT'/" gsmap_24hr_rain.gs
sed -i "3s/.*/date3='${FCST_YY}-${FCST_MM}-${FCST_DD}_$FCST_ZZ'/" gsmap_24hr_rain.gs
sed -i "4s~.*~outdir='${VAL_OUTDIR}'~" gsmap_24hr_rain.gs
sed -i "5s/.*/data='${GSMAP_DATA}'/" gsmap_24hr_rain.gs
sed -i "6s~.*~'sdfopen ${VAL_DIR}/gsmap/nc/gsmap_'data'_'date3'.nc'~" gsmap_24hr_rain.gs

grads -pbc gsmap_24hr_rain.gs

# Get hourly data over stations
rm -rf $VAL_OUTDIR/gsmap_${DATE_STR1}PHT*.csv

# Edit GrADS extract script
sed -i "1s/.*/date='${DATE_STR1}PHT'/" gsmap_extract_rain.gs
sed -i "2s/.*/dfile='${FCST_YY}-${FCST_MM}-${FCST_DD}_$FCST_ZZ'/" gsmap_extract_rain.gs
sed -i "3s~.*~outdir='${VAL_OUTDIR}'~" gsmap_extract_rain.gs
sed -i "4s~.*~gsmapdir='${VAL_DIR}/gsmap/nc'~" gsmap_extract_rain.gs
sed -i "5s/.*/data='${GSMAP_DATA}'/" gsmap_extract_rain.gs
grads -pbc gsmap_extract_rain.gs

echo "--------------------------"
echo " Done with GSMaP!         "
echo "--------------------------"
# -------------------------------------------- #
#                   GFS                        #
# -------------------------------------------- #
echo "--------------------------"
echo " Processing GFS files...  "
echo "--------------------------"

cd ${VAL_DIR}/gfs

# Convert GFS precipitation grb files to .nc
./convert_gfs_nc.sh

# Plot GFS
mkdir -p $VAL_OUTDIR
cd ${VAL_DIR}/grads

# Edit GrADS plotting script
DATE_STR1=$(date -d "${FCST_YY}-${FCST_MM}-${FCST_DD} $FCST_ZZ:00:00 8 hours" +'%Y-%m-%d_%H')
read FCST_YY_PHT FCST_MM_PHT FCST_DD_PHT FCST_HH_PHT <<< ${DATE_STR1//[-_]/ }

sed -i "1s/.*/date='${DATE_STR1}PHT'/" gfs_24hr_rain.gs
sed -i "2s/.*/date2='${DATE_STR1} PHT'/" gfs_24hr_rain.gs
sed -i "3s/.*/date3='${FCST_YY}-${FCST_MM}-${FCST_DD}_$FCST_ZZ'/" gfs_24hr_rain.gs
sed -i "4s~.*~outdir='${VAL_OUTDIR}'~" gfs_24hr_rain.gs
sed -i "5s~.*~gfsdir='${VAL_DIR}/gfs/nc/${FCST_YY}${FCST_MM}${FCST_DD}/${FCST_ZZ}'~" gfs_24hr_rain.gs

grads -pbc gfs_24hr_rain.gs

# Get hourly data over stations
rm -rf $VAL_OUTDIR/gfs_${DATE_STR1}PHT*.csv

# Edit GrADS extract script
sed -i "1s/.*/date='${DATE_STR1}PHT'/" gfs_extract_rain.gs
sed -i "2s~.*~outdir='${VAL_OUTDIR}'~" gfs_extract_rain.gs
sed -i "3s~.*~gfsdir='${VAL_DIR}/gfs/nc/${FCST_YY}${FCST_MM}${FCST_DD}/${FCST_ZZ}'~" gfs_extract_rain.gs

grads -pbc gfs_extract_rain.gs

echo "--------------------------"
echo " Done with GFS!           "
echo "--------------------------"
# -------------------------------------------- #
#            COMPARISON PLOTS                  #
# -------------------------------------------- #
echo "---------------------------------"
echo " Processing comparison plots...  "
echo "---------------------------------"

# 24-hr difference plot (WRF-GSMaP, GFS-GSMaP)
cd ${VAL_DIR}/grads

ln -s ${WRF_ENS}/wrffcst_d01_${FCST_YY}-${FCST_MM}-${FCST_DD}_${FCST_ZZ}_ens.nc ${VAL_DIR}/grads/nc/.

# Edit GrADS plotting script
sed -i "1s/.*/date='${DATE_STR1}PHT'/" bias_24hr_rain.gs
sed -i "2s/.*/date2='${DATE_STR1} PHT'/" bias_24hr_rain.gs
sed -i "3s/.*/date3='${FCST_YY}-${FCST_MM}-${FCST_DD}_$FCST_ZZ'/" bias_24hr_rain.gs
sed -i "4s~.*~outdir='${VAL_OUTDIR}'~" bias_24hr_rain.gs
sed -i "5s~.*~wrfdir='nc'~" bias_24hr_rain.gs

grads -pbc bias_24hr_rain.gs

# 24-hr timeseries plot (WRF, GFS, GSMaP)
cd ${VAL_DIR}/timeseries

# Edit concatenating csv script
sed -i "4s/.*/yyyymmdd = '${FCST_YY_PHT}-${FCST_MM_PHT}-${FCST_DD_PHT}'/" concat_rain.py
sed -i "5s/.*/init = '${FCST_HH_PHT}'/" concat_rain.py
sed -i "6s~.*~IN_DIR = '${VAL_OUTDIR}'~" concat_rain.py
sed -i "7s~.*~OUT_DIR = '${VAL_OUTDIR}'~" concat_rain.py

# Concatenate csv
$PYTHONCONDA concat_rain.py

# Edit time series plotting script
sed -i "7s/.*/yyyymmdd = '${FCST_YY_PHT}-${FCST_MM_PHT}-${FCST_DD_PHT}'/" timeseries_plot.py
sed -i "8s/.*/init = '${FCST_HH_PHT}'/" timeseries_plot.py
sed -i "9s~.*~FCST_DIR = '${OUTDIR}/timeseries/csv/${FCST_YY}${FCST_MM}${FCST_DD}/${FCST_ZZ}'~" timeseries_plot.py
sed -i "10s~.*~CSV_DIR = '${VAL_OUTDIR}'~" timeseries_plot.py
sed -i "11s~.*~OUT_DIR = '${VAL_OUTDIR}'~" timeseries_plot.py
sed -i "12s/.*/stn = '${STATION_ID}'/" timeseries_plot.py
sed -i "13s/.*/station = '${STATION_NAME}'/" timeseries_plot.py

# Plot 24hr time series
export MPLBACKEND="agg"; $PYTHONCONDA timeseries_plot.py

echo "--------------------------"
echo " Done with comparison!    "
echo "--------------------------"
# -------------------------------------------- #
#            CONTINGENCY TABLE                 #
# -------------------------------------------- #
echo "---------------------------------"
echo " Processing contingency plot...  "
echo "---------------------------------"

cd ${VAL_DIR}/grads/nc
$CDO remapbil,wrf_24hr_rain_day1_${DATE_STR1}PHT.nc gsmap_24hr_rain_day1_${DATE_STR1}PHT.nc gsmap_24hr_rain_day1_${DATE_STR1}PHT_re.nc

cd ${VAL_DIR}/contingency

# Edit contingency script
sed -i "4s/.*/yyyymmdd = '${FCST_YY_PHT}-${FCST_MM_PHT}-${FCST_DD_PHT}'/" forecast_verification.py
sed -i "5s/.*/init = '${FCST_HH_PHT}'/" forecast_verification.py
sed -i "6s~.*~EXTRACT_DIR = '${VAL_DIR}/grads/nc'~" forecast_verification.py
sed -i "7s~.*~OUT_DIR = '${VAL_OUTDIR}'~" forecast_verification.py

# Plot contingency table
export MPLBACKEND="agg"; $PYTHONCONDA forecast_verification.py

echo "---------------------------"
echo " Done with contingency!    "
echo "---------------------------"

# -------------------------------------------- #
#              CLEAN UP FILES                  #
# -------------------------------------------- #
rm ${VAL_DIR}/grads/nc/*.nc
rm ${VAL_DIR}/gsmap/dat/*.dat
# rm ${VAL_DIR}/gsmap/nc/*.nc
rm ${VAL_DIR}/gsmap/log/*.log
rm ${VAL_DIR}/gfs/nc/${FCST_YY}${FCST_MM}${FCST_DD}/${FCST_ZZ}/*.nc 
echo "----------------------"
echo " Validation finished! "
echo "----------------------"
cd ${VALDIR}