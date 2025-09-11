import warnings
from pathlib import Path
from typing import Optional, Union
import numpy.typing as npt
import netCDF4
import xarray as xr

import numpy as np
from wrf import getvar, interplevel, ALL_TIMES
import metpy.calc as mpcalc
from metpy.units import units


RAW_VARS = (
    "RAINC",
    "RAINNC",
    "T2",
    "TSK",
    "PSFC",
    "Q2",
    "HGT",
    "P",
    "PH",
    "PB",
    "PHB",
    "U",
    "V",
    "SWDDNI",
    "COSZEN",
    "SWDDIF",
    "U10",
    "V10",
)

DERIVED_VARS = {
    "prcp": ("RAINC", "RAINNC"),
    "tsk": ("TSK",),
    "hi": ("rh2",),
    "hix": ("rh2",),
    "rh2": ("T2", "PSFC", "Q2"),
    "ua": ("U"),
    "va": ("V"),
    "u10": ("U10"),
    "v10": ("V10"),
    "height_agl": ("P", "PH", "PHB", "HGT"),
    "pressure": ("P", "PB"),
    "u_850hPa": ("ua", "pressure"),
    "v_850hPa": ("va", "pressure"),
    "u_80m": ("ua", "height_agl"),
    "v_80m": ("va", "height_agl"),
    "wpd": ("u_80m", "v_80m"),
    "ppv": ("T2", "SWDDNI", "COSZEN", "SWDDIF"),
    "ghi": ("SWDDNI", "COSZEN", "SWDDIF"),
}


def get_required_variables(var_name: str) -> tuple[str]:
    """Get required variables.

    Args:
        var_name (str): A valid raw or derived variable name.

    Returns:
        tuple[str]: List required variables.
    """
    v = []
    if var_name in DERIVED_VARS:
        for _v in DERIVED_VARS[var_name]:
            v.extend(get_required_variables(_v))
    elif var_name in RAW_VARS:
        v.append(var_name)
    else:
        warnings.warn("Not a valid variable name, skipping.")
    return tuple(set(v))


def create_wrfout_subset(
    nc_in: Union[Path, str],
    nc_out: Union[Path, str],
    raw_variables: Optional[list[str]] = None,
    derived_variables: Optional[list[str]] = None,
    overwrite=False,
):
    """Create a subset of wrfout

    Args:
        nc_in (Path or str): Input wrfout.
        nc_out (Path or str): Output wrfout subset.
        raw_variables (list[str], optional): Raw variables to include. Defaults to None.
        derived_variables (list[str], optional): Derived variable to include.
            Defaults to None.
        overwrite (bool, optional): Overwrite the file if it exists. Defaults to False.
    """
    ds = xr.open_dataset(nc_in)

    if isinstance(nc_out, str):
        nc_out = Path(nc_out)

    vars: list[str] = ["Times"]
    if raw_variables is not None:
        vars.extend(raw_variables)
    if derived_variables is not None:
        for var_name in derived_variables:
            vars.extend(get_required_variables(var_name))
    vars = list(set(vars))
    if len(vars) == 1:
        vars.extend(RAW_VARS)

    ds_out = ds[vars]
    time_bnd = (0, 24 + 1)
    level_bnd = (0, 10)
    if "Time" in ds_out.dims:
        ds_out = ds_out.sel(Time=slice(*time_bnd))
    if "bottom_top" in ds_out.dims:
        ds_out = ds_out.sel(bottom_top=slice(*level_bnd))
    if "bottom_top_stag" in ds_out.dims:
        ds_out = ds_out.sel(bottom_top_stag=slice(level_bnd[0], level_bnd[1] + 1))
    if overwrite:
        nc_out.unlink(missing_ok=True)
    ds_out.to_netcdf(nc_out)


def wrf_getvar(
    wrfin,
    varname: str,
    timeidx: Optional[int] = ALL_TIMES,
    levels: Optional[npt.NDArray[np.float32]] = None,
    interp: Optional[str] = None,
) -> xr.DataArray:
    """Wrapper around wrf-python's getvar

    Args:
        wrfin (netCDF4.Dataset or an Iterable]): WRF-ARW NetCDF data.
        varname (str): The variable name.
        timeidx (int, optional): The desired time index. Defaults to ALL_TIMES.
        levels (numpy.NDArray[float], optional): Desired levels. Defaults to None.
        interp (str, optional): Type of vertical interpolation. Defaults to None.

    Returns:
        xarray.DataArray: The extracted variable.
    """
    required_variables = get_required_variables(varname)
    res_shape = None
    ens_names = [1]
    wrfins = []
    if isinstance(wrfin, dict):
        ens_names = [i for i in range(len(wrfin.keys()))]
        wrfins = [v for v in wrfin.values()]
    if isinstance(wrfin, list) or isinstance(wrfin, tuple):
        ens_names = [i for i in range(len(wrfin))]
        wrfins = [v for v in wrfin]
    elif isinstance(wrfin, netCDF4.Dataset):
        wrfins = [wrfin]

    res_shape = wrfins[0].variables[required_variables[0]].shape

    dat: list[xr.DataArray] = []
    for _wrfin in wrfins:
        if timeidx is ALL_TIMES:
            _dat = []
            for t in range(res_shape[0]):
                _dat.append(_wrf_getvar(_wrfin, varname, t, levels, interp))
            dat.append(xr.concat(_dat, dim="time"))
        else:
            dat.append(_wrf_getvar(_wrfin, varname, timeidx, levels, interp))

    if len(dat) > 1:
        return xr.concat(dat, xr.DataArray(ens_names, coords=[ens_names], dims=["ens"]))
    return dat[0]


def _wrf_getvar(
    wrfin: netCDF4.Dataset,
    varname: str,
    timeidx=0,
    levels: Optional[npt.NDArray[np.float32]] = None,
    interp: Optional[str] = None,
) -> xr.DataArray:
    """Internal wrapper around wrf-python's getvar

    Args:
        wrfin (netCDF4.Dataset): WRF-ARW NetCDF data.
        varname (str): The variable name.
        timeidx (int, optional): The desired time index. Defaults to 0.
        levels (numpy.NDArray[float], optional): Desired levels. Defaults to None.
        interp (str, optional): Type of vertical interpolation. Defaults to None.

    Returns:
        xarray.DataArray: The extracted variable.
    """
    if varname == "prcp":
        da = getvar(wrfin, "RAINC", timeidx) + getvar(wrfin, "RAINNC", timeidx).values
        da.name = "prcp"
    elif varname == "hi":
        t = getvar(wrfin, "T2", timeidx) - 273.15
        rh = getvar(wrfin, "rh2", timeidx)
        da = heat_index(t, rh)
        da.name = "hi"
    elif varname == "wpd":
        u = _wrf_getvar(wrfin, "ua", timeidx, levels=80, interp="height_agl")
        v = _wrf_getvar(wrfin, "va", timeidx, levels=80, interp="height_agl")
        wspd = u.copy()
        wspd.values = (u.values**2 + v.values**2) ** 0.5
        da = wind_power_density(wspd)
        da.name = "wpd"
    elif varname == "ppv":
        swddni = getvar(wrfin, "SWDDNI", timeidx)
        coszen = getvar(wrfin, "COSZEN", timeidx)
        swddif = getvar(wrfin, "SWDDIF", timeidx)
        t = getvar(wrfin, "T2", timeidx) - 273.15
        da = pv_power_potential(swddni, coszen, swddif, t)
        da.name = "ppv"
    elif varname == "ghi":
        swddni = getvar(wrfin, "SWDDNI", timeidx)
        coszen = getvar(wrfin, "COSZEN", timeidx)
        swddif = getvar(wrfin, "SWDDIF", timeidx)
        da = global_horizontal_irradiance(swddni, coszen, swddif)
        da.name = "ghi"
    else:
        da = getvar(wrfin, varname, timeidx)

    if levels is not None:
        if interp in ["pressure", "height", "height_agl"]:
            vert = getvar(wrfin, interp, timeidx)
        da = interplevel(da, vert, levels)

    tr = {
        "Time": "time",
        "XLAT": "lat",
        "XLONG": "lon",
        "XTIME": "xtime",
    }
    tr = {k: tr[k] for k in tr.keys() if k in da.coords}
    da = da.rename(tr)
    return da


def heat_index(t: xr.DataArray, rh: xr.DataArray) -> xr.DataArray:
    """Computes Heat Index based on Rothfusz (1990).

    Args:
        t (xarray.DataArray): Air Temperature in °C.
        rh (xarray.DataArray): Relative Humidity.

    Returns:
        xarray.DataArray: Heat Index in °C.
    """
    _t = t * units.degC
    _rh = rh * units.percent
    hi = mpcalc.heat_index(
        _t,
        _rh,
    )
    return hi.metpy.convert_units(units.degC).metpy.dequantify()


def wind_power_density(wspd: xr.DataArray) -> xr.DataArray:
    """Computes wind power density

    Args:
        wspd (xarray.DataArray): Wind speed in m/s

    Returns:
        xarray.DataArray: Wind Power Density in MW
    """
    a = 0.5  # constant
    rho = 1.23  # air density
    # r = 52  # blade length of turbine (radius)
    cp = 0.4  # power coefficient
    # cf = 0.4  # cf = capacity factor (40%)
    turb = 4  # assume 4 wind turbines in one hectare
    swarea = 8495  # swept area of turbine

    wpd = turb * (a * rho * swarea * cp * wspd**3)
    return wpd / 1000000


def pv_power_potential(
    swddni: xr.DataArray, coszen: xr.DataArray, swddif: xr.DataArray, t: xr.DataArray
) -> xr.DataArray:
    """Computes PV Power Potential

    Args:
        swddni (xarray.DataArray): [description]
        coszen (xarray.DataArray): [description]
        swddif (xarray.DataArray): [description]
        t (xarray.DataArray): 2m Air temperature in °C

    Returns:
        xarray.DataArray: [description]
    """
    c1 = -3.75
    c2 = 1.14
    c3 = 0.0175
    beta = 0.0045
    gamma = 0.1
    t_ref = 25.0
    eta_ref = 0.12

    ghi = (swddni * coszen.values) + swddif.values
    t_cell = c1 + c2 * t + c3 * ghi.values
    eta_cell = eta_ref * (1 - beta * (t_cell - t_ref) + gamma * np.log10(ghi.values))
    ppv = ghi * eta_cell.values

    # adjust to number of solar panels in 1 hectare = 7200
    # adjust to MW
    spanel = 7200
    # cf = 0.2
    return ppv * spanel / 1000000


def global_horizontal_irradiance(
    swddni: xr.DataArray, coszen: xr.DataArray, swddif: xr.DataArray
) -> xr.DataArray:
    """Computes Global Horizontal Irradiance (W m-2)

    Args:
        swddni (xarray.DataArray): [description]
        coszen (xarray.DataArray): [description]
        swddif (xarray.DataArray): [description]

    Returns:
        xarray.DataArray: [description]
    """

    ghi = (swddni * coszen.values) + swddif.values

    return ghi
