import pvlib
import pandas as pd
import matplotlib.pyplot as plt
from pvlib.location import Location
from pvlib.pvsystem import PVSystem
from pvlib.modelchain import ModelChain

lat, lon = 39.9, 116.4
tz = 'Asia/Shanghai'
site = Location(latitude=lat, longitude=lon, tz=tz, altitude=44, name='Beijing')

times = pd.date_range(start='2024-06-21', end='2024-06-22', freq='15min', tz=tz)
clearsky = site.get_clearsky(times)

weather = pd.DataFrame({
    'ghi': clearsky['ghi'],
    'dni': clearsky['dni'],
    'dhi': clearsky['dhi'],
    'temp_air': 30,
    'wind_speed': 2
}, index=times)

sandia_modules = pvlib.pvsystem.retrieve_sam('SandiaMod')
module_params = sandia_modules['Canadian_Solar_CS5P_220M___2009_']

cec_inverters = pvlib.pvsystem.retrieve_sam('cecinverter')
inverter_params = cec_inverters['ABB__MICRO_0_25_I_OUTD_US_208__208V_']

system = PVSystem(
    surface_tilt=30,
    surface_azimuth=180,
    module_parameters=module_params,
    inverter_parameters=inverter_params,
    racking_model='open_rack',
    module_type='glass_polymer'
)

mc = ModelChain(system, site)
mc.run_model(weather)

print("模拟完成！当日最大 AC 输出功率为: ", mc.results.ac.max(), "W")

mc.results.ac.plot(figsize=(10, 6), title='Summer Solstice Clear Sky Power Output (Beijing)')
plt.ylabel('AC Power Output (Watts)')
plt.xlabel('Time of Day')
plt.grid(True)
plt.show()