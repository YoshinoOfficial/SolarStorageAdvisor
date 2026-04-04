import matplotlib.pyplot as plt
import matplotlib as mpl

# 配置中文字体
mpl.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
mpl.rcParams['axes.unicode_minus'] = False

def plot_comparison(data, ifsave=False):
    '''
    # 获取数据
    Solar = getsolar()
    Consumption = getconsumption()

    # 创建 DataFrame
    data = pd.DataFrame({
        'Solar': Solar.values,
        'Consumption': Consumption.values
    }, index=Solar.index)'''

    # 创建图形和子图
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), gridspec_kw={'height_ratios': [2, 1]})
    
    # 使用颜色字典
    color_dict = {
        'Solar': '#1f77b4',
        'Wind': '#17becf',
        'Consumption': '#ff7f0e',
        'Energy Balance': '#2ca02c',
        'Storage Power': '#9467bd',
        'Net Load': '#8c564b'
    }
    
    # 上图：功率曲线
    power_cols = ['Solar', 'Wind', 'Consumption', 'Storage Power', 'Net Load']
    power_cols_exist = [col for col in power_cols if col in data.columns]
    
    for col in power_cols_exist:
        ax1.plot(data.index, data[col], label=col, color=color_dict.get(col, '#333333'), linewidth=2)
    
    ax1.set_ylabel('Power (kW)', fontsize=12)
    ax1.set_xlabel('Time', fontsize=12)
    ax1.set_title('Solar Power, Consumption and Storage', fontsize=14, fontweight='bold')
    ax1.legend(loc='best', fontsize=10)
    ax1.grid(True, alpha=0.3)
    
    # 下图：SOC曲线
    if 'SOC' in data.columns:
        ax2.plot(data.index, data['SOC'] * 100, label='SOC', color='#d62728', linewidth=2)
        ax2.fill_between(data.index, 0, data['SOC'] * 100, alpha=0.3, color='#d62728')
        ax2.set_ylabel('SOC (%)', fontsize=12)
        ax2.set_xlabel('Time', fontsize=12)
        ax2.set_title('Battery State of Charge', fontsize=14, fontweight='bold')
        ax2.legend(loc='best', fontsize=10)
        ax2.grid(True, alpha=0.3)
        ax2.set_ylim(0, 100)
    
    plt.tight_layout()
    plt.show(block=False)
    
    if ifsave:
        plt.savefig('comparison.png', dpi=300, bbox_inches='tight')
    
    plt.pause(5)
    plt.close()