from Solar.Solar import getsolar
from Consumption.Consumption import getconsumption
from Wind.Wind import getwind
from Storage.Storage import simulate_storage
from config.config_manager import load_electricity_price
import pandas as pd
from plot_comparison import plot_comparison

freconvert = 60 / 15

def get_simulation_data():
    Solar = getsolar(start="2010-06-01", end="2010-06-02")
    Consumption = getconsumption(start="2010-06-01", end="2010-06-02")
    Wind = getwind(start="2010-06-01", end="2010-06-01")
    
    data = pd.DataFrame({
        'Solar': Solar.values,
        'Wind': Wind.values,
        'Consumption': Consumption.values,
        'Energy Balance': Consumption.values - Solar.values - Wind.values
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
    cost = cost - calculate_renewable_revenue(data)['revenue_from_selling']
    return cost

def calculate_renewable_revenue(data):
    economics_config = load_electricity_price()
    electricity_price = economics_config['electricity_price']
    feed_in_price = economics_config.get('feed_in_price', 0.4)
    
    purchase_electricity = data['Net Load'].clip(lower=0)
    sell_electricity = (-data['Net Load']).clip(lower=0)
    
    reduced_purchase = data['Consumption'] - purchase_electricity
    
    revenue_from_reduced_purchase = float(sum(reduced_purchase * electricity_price) / freconvert)
    revenue_from_selling = float(sum(sell_electricity * feed_in_price) / freconvert)
    
    total_revenue = revenue_from_reduced_purchase + revenue_from_selling
    
    return {
        'total_revenue': total_revenue,
        'revenue_from_reduced_purchase': revenue_from_reduced_purchase,
        'revenue_from_selling': revenue_from_selling,
        'reduced_purchase_kwh': float(sum(reduced_purchase) / freconvert),
        'sell_electricity_kwh': float(sum(sell_electricity) / freconvert)
    }

if __name__ == '__main__':
    economics_config = load_electricity_price()
    data = get_simulation_data()
    cost = calculate_daily_cost(data)
    revenue = calculate_renewable_revenue(data)
    print(f"成本为: {cost} 元/天")
    print(f"新能源收益: {revenue['total_revenue']} 元/天")
    print(f"  - 减少购电收益: {revenue['revenue_from_reduced_purchase']} 元/天")
    print(f"  - 售电收益: {revenue['revenue_from_selling']} 元/天")
    plot_comparison(data, ifsave=True)
