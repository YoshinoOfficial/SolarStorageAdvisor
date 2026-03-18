import matplotlib.pyplot as plt
import matplotlib as mpl

# 配置中文字体
mpl.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
mpl.rcParams['axes.unicode_minus'] = False

def plot_comparison(data,ifsave=False):
    '''
    # 获取数据
    Solar = getsolar()
    Consumption = getconsumption()

    # 创建 DataFrame
    data = pd.DataFrame({
        'Solar': Solar.values,
        'Consumption': Consumption.values
    }, index=Solar.index)'''


    # 使用颜色字典
    color_dict = {
        'Solar': '#1f77b4',    # 蓝色
        'Consumption': '#ff7f0e',    # 橙红色
        'Energy Balance': '#2ca02c'    # 绿色
    }

    data.plot(
        figsize=(12, 6),
        title='Solar Power vs Consumption',
        color=[color_dict[col] for col in data.columns],
        linewidth=2
    )

    plt.ylabel('Power (kW/平方米)')
    plt.xlabel('Time')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show(block=False)
    if ifsave:
        plt.savefig('comparison.png')
    plt.pause(5)
    plt.close()