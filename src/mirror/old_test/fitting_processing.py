import pandas as pd
import numpy as np
from scipy.stats import linregress
import matplotlib.pyplot as plt

import pandas as pd
import numpy as np
from scipy.stats import linregress
import matplotlib.pyplot as plt

# 设置支持中文的字体
try:
    # 尝试使用系统安装的中文字体
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'WenQuanYi Micro Hei', 'sans-serif']
    plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题
    print("✅ 已设置中文字体支持")
except:
    print("⚠️ 无法设置中文字体，将使用英文替代")

def find_linear_relationship(csv_file, x_col, y_col):
    """
    寻找线性关系 y = mx + b
    """
    df = pd.read_csv(csv_file)
    x = df[x_col]
    y = df[y_col]
    
    # 线性回归
    slope, intercept, r_value, p_value, std_err = linregress(x, y)
    
    print("🔍 线性关系分析")
    print("=" * 40)
    print(f"回归方程: y = {slope:.6f}x + {intercept:.6f}")
    print(f"相关系数 R: {r_value:.6f}")
    print(f"确定系数 R²: {r_value**2:.6f}")
    print(f"斜率标准差: {std_err:.6f}")
    print(f"P值: {p_value:.6f}")
    
    # 预测值
    y_pred = slope * x + intercept
    
    # 计算残差（实际值 - 预测值）
    residuals = y - y_pred
    print(f"残差标准差: {residuals.std():.6f}")
    
    # 可视化
    plt.figure(figsize=(12, 5))
    
    plt.subplot(1, 2, 1)
    plt.scatter(x, y, alpha=0.6, label='Actual_Data')
    plt.plot(x, y_pred, color='red', linewidth=2, label=f'y = {slope:.4f}x + {intercept:.4f}')
    plt.xlabel(x_col)
    plt.ylabel(y_col)
    plt.legend()
    plt.title('Linear regression fitting')  # 线性回归拟合
    plt.grid(True, alpha=0.3)
    
    plt.subplot(1, 2, 2)
    plt.scatter(y_pred, residuals, alpha=0.6)
    plt.axhline(y=0, color='red', linestyle='--')
    plt.xlabel('Predicted Values')  # 预测值
    plt.ylabel('Residuals')         # 残差
    plt.title('Residual Plot')      # 残差图
    plt.grid(True, alpha=0.3)
    
    # plt.tight_layout()
    # 显示图表
    plt.savefig(f'data/1.png', dpi=300, bbox_inches='tight') # 保存为PNG文件
    # plt.show()
    
    return slope, intercept, residuals

if __name__ == "__main__":
    # 使用示例
    slope, intercept, residuals = find_linear_relationship('data/data_20260510_220337.csv', 'Steps', 'Force_Value')
