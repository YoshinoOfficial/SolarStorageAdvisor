from Solar.Solar import getsolar
from Consumption.Consumption import getconsumption
from Storage.Storage import simulate_storage
from config.config_manager import load_electricity_price
import pandas as pd
from plot_comparison import plot_comparison

freconvert = 60 / 15

def get_simulation_data():
    Solar = getsolar()
    Consumption = getconsumption()
    
    data = pd.DataFrame({
        'Solar': Solar.values,
        'Consumption': Consumption.values,
        'Energy Balance': Consumption.values - Solar.values
    }, index=Solar.index)
    
    storage_power, soc = simulate_storage(data['Energy Balance'], freq_minutes=15)
    data['Storage Power'] = storage_power.values
    data['SOC'] = soc.values
    data['Net Load'] = data['Energy Balance'] + data['Storage Power']
    
    return data

def calculate_daily_cost(data):
    economics_config = load_electricity_price()
    Electricity = data['Net Load'].clip(lower=0)
    ElectricityPrice = economics_config['electricity_price']
    cost = float(sum(Electricity * ElectricityPrice) / freconvert)
    return cost

if __name__ == '__main__':
    economics_config = load_electricity_price()
    data = get_simulation_data()
    cost = calculate_daily_cost(data)
    print(f"成本为: {cost} 元/天")
    plot_comparison(data, ifsave=True)
