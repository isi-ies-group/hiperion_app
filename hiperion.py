# -*- coding: utf-8 -*-
"""
Created on Mon Jul  5 11:22:36 2021

@author: Ruben
"""
import streamlit as st
import pandas as pd
import numpy as np

# st.title('Uber pickups in NYC')

# DATE_COLUMN = 'date/time'
# DATA_URL = ('https://s3-us-west-2.amazonaws.com/'
#             'streamlit-demo-data/uber-raw-data-sep14.csv.gz')

# @st.cache
# def load_data(nrows):
#     data = pd.read_csv(DATA_URL, nrows=nrows)
#     lowercase = lambda x: str(x).lower()
#     data.rename(lowercase, axis='columns', inplace=True)
#     data[DATE_COLUMN] = pd.to_datetime(data[DATE_COLUMN])
#     return data

# data_load_state = st.text('Loading data...')
# data = load_data(10000)
# data_load_state.text("Done! (using st.cache)")

# if st.checkbox('Show raw data'):
#     st.subheader('Raw data')
#     st.write(data)

# st.subheader('Number of pickups by hour')
# hist_values = np.histogram(data[DATE_COLUMN].dt.hour, bins=24, range=(0,24))[0]
# st.bar_chart(hist_values)

# # Some number in the range 0-23
# hour_to_filter = st.slider('hour', 0, 23, 17)
# filtered_data = data[data[DATE_COLUMN].dt.hour == hour_to_filter]

# st.subheader('Map of all pickups at %s:00' % hour_to_filter)
# st.map(filtered_data)


# %%
import matplotlib.pyplot as plt
import pvlib

from cpvlib import cpvsystem
from module_parameters import mod_params_cpv, mod_params_flatplate

st.title('HIPERION Workshop model')


coordenadas = {'Madrid': (40.4, -3.7),
               'Almeria': (36.86, -2.48),
               'Laussane': (46.53, 6.61),
               'Edinburgh': (55.97, -3.18),
               'Tamanraset': (23.00, 3.78)
               }

# t = st.empty()

ciudad = st.radio('Radio', list(coordenadas.keys()))
lat, lon = coordenadas[ciudad]
st.write(ciudad)
st.write(lat)
st.write(lon)

print(lat, lon)

# lat = st.slider('Latitude', min_value=10.0, max_value=50.0, value=lat)

data_pvgis = pvlib.iotools.get_pvgis_tmy(lat, lon)

data = data_pvgis[0].rename(columns={
    'Gb(n)': 'dni',
    'G(h)': 'ghi',
    'Gd(h)': 'dhi',
    'T2m': 'temp_air',
    'WS10m': 'wind_speed',
})

data = data.set_index(
    data.index.map(lambda t: t.replace(year=2010)))

location = pvlib.location.Location(
    latitude=lat, longitude=lon, altitude=695, tz='utc')

solar_zenith = location.get_solarposition(data.index).zenith
solar_azimuth = location.get_solarposition(data.index).azimuth

# %%
# StaticHybridSystem
static_hybrid_sys = cpvsystem.StaticHybridSystem(
    surface_tilt=30,
    surface_azimuth=180,
    module_cpv=None,
    module_flatplate=None,
    module_parameters_cpv=mod_params_cpv,
    module_parameters_flatplate=mod_params_flatplate,
    modules_per_string=1,
    strings_per_inverter=1,
    inverter=None,
    inverter_parameters=None,
    racking_model="insulated",
    losses_parameters=None,
    name=None,
)

# get_effective_irradiance
data['dii_effective'], data['poa_flatplate_static_effective'] = static_hybrid_sys.get_effective_irradiance(
    solar_zenith,
    solar_azimuth,
    # iam_param=0.7,
    # aoi_limit=55,
    dii=None,
    ghi=data['ghi'],
    dhi=data['dhi'],
    dni=data['dni']
)

# pvsyst_celltemp
data['temp_cell_35'], data['temp_cell_flatplate'] = static_hybrid_sys.pvsyst_celltemp(
    dii=data['dii_effective'],
    poa_flatplate_static=data['poa_flatplate_static_effective'],
    temp_air=data['temp_air'],
    wind_speed=data['wind_speed']
)

# calcparams_pvsyst
diode_parameters_cpv, diode_parameters_flatplate = static_hybrid_sys.calcparams_pvsyst(
    dii=data['dii_effective'],
    poa_flatplate_static=data['poa_flatplate_static_effective'],
    temp_cell_cpv=data['temp_cell_35'],
    temp_cell_flatplate=data['temp_cell_flatplate'],
)

# singlediode
dc_cpv, dc_flatplate = static_hybrid_sys.singlediode(
    diode_parameters_cpv, diode_parameters_flatplate)

# uf_global (uf_am, uf_temp_air)
data['am'] = location.get_airmass(data.index).airmass_absolute

uf_cpv = static_hybrid_sys.get_global_utilization_factor_cpv(
    data['am'], data['temp_air'])

# Power
cpv_days = dc_cpv['2010-06-15':'2010-06-20']
uf_cpv_days = uf_cpv['2010-06-15':'2010-06-20']
flatplate_days = dc_flatplate['2010-06-15':'2010-06-20']
data_days = data['2010-06-15':'2010-06-20']

fig, axs = plt.subplots(2)

# (cpv_days.p_mp * uf_cpv_days).plot(ax=axs[0], legend=True, label="CPV")
# flatplate_days.p_mp.plot(ax=axs[0], secondary_y=True, legend=True, label="Flat plate")
# data_days[['dni', 'dhi']].plot(ax=axs[1], linewidth=1)

st.line_chart(cpv_days.p_mp * uf_cpv_days)

# Energy
energy_cpv = (dc_cpv['p_mp'] * uf_cpv).sum()
energy_flatplate = dc_flatplate['p_mp'].sum()

st.write(energy_cpv)

# print(f"E_CPV={energy_cpv:.0f} Wh", f"E_diff={energy_flatplate:.0f} Wh")
