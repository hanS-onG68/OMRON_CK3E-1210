import matplotlib
# 必须放在import matplotlib.pyplot之前，无桌面环境专用非交互式后端
matplotlib.use('Agg')

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from scipy.stats import pearsonr, spearmanr, linregress
from mirror.logger import setup_logger

logger = setup_logger()


class DataAnalyzer:
    """数据分析类，包含相关性分析和趋势图绘制"""
    def __init__(self, csv_file):
        self.csv_file = csv_file
        self.df = pd.read_csv(csv_file)  # 读取CSV文件
        self.pearson_corr = None         # 皮尔逊相关系数的r值
        self.pearson_p = None            # 皮尔逊相关系数的p值
        self.spearman_corr = None        # 斯皮尔曼相关系数的r值
        self.spearman_p = None           # 斯皮尔曼相关系数的p值
    

    def is_linear_relationship(self, x_col, y_col)-> bool:
        """
        判断是否为线性关系
        """
        # 计算相关系数
        self.pearson_corr, self.pearson_p = pearsonr(self.df[x_col], self.df[y_col])     # 皮尔逊相关系数
        self.spearman_corr, self.spearman_p = spearmanr(self.df[x_col], self.df[y_col])  # 斯皮尔曼相关系数
        logger.info(f"皮尔逊相关系数: {self.pearson_corr:.4f} (p={self.pearson_p:.4f})")
        logger.info(f"斯皮尔曼相关系数: {self.spearman_corr:.4f} (p={self.spearman_p:.4f})")

        if self.pearson_p < 0.05 and self.spearman_p < 0.05:      # 看结果时，通常先看 p 值判断结果是否可信，如果可信，再看 corr 值判断相关性的方向和强弱。
            logger.info("✅ 相关性显著, 结果可信")
            if abs(self.pearson_corr) > 0.6 and abs(self.spearman_corr) > 0.6:
                logger.info("🔗 相关性强")
                return True
        else:
            logger.warning("⚠️ 相关性不显著，结果可能不可靠")
        return False
    
    def plot_linear_relationship(self, x_col, y_col):
        """
        寻找线性关系 y = mx + b
        """
        x = self.df[x_col]
        y = self.df[y_col]

        # 线性回归
        slope, intercept, r_value, p_value, std_err = linregress(x, y)
        
        logger.info("🔍 线性关系分析")
        logger.info("=" * 40)
        logger.info(f"回归方程: y = {slope:.6f}x + {intercept:.6f}")
        logger.info(f"相关系数 R: {r_value:.6f}")
        logger.info(f"确定系数 R²: {r_value**2:.6f}")
        logger.info(f"斜率标准差: {std_err:.6f}")
        logger.info(f"P值: {p_value:.6f}")
        
        # 预测值
        y_pred = slope * x + intercept
        
        # 计算残差（实际值 - 预测值）
        residuals = y - y_pred
        logger.info(f"残差标准差: {residuals.std():.6f}")
        
        # 可视化
        plt.figure(figsize=(12, 6))
        
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
        
        plt.tight_layout()

        # 显示图表
        plt.savefig(f'{self.csv_file}_2.png', dpi=300, bbox_inches='tight') # 保存为PNG文件
        # plt.show()
        plt.close() # 释放内存
        
        return slope, intercept, residuals

    def plot_data_trend(self, x_col: str, y_col: str):
        """
        使用Matplotlib绘制数据变化趋势图
        """
        logger.info(f"📊 正在绘制图表，数据形状: {self.df.shape}")
        
        # 创建图形
        plt.figure(figsize=(12, 6))
        
        # 绘制趋势线
        plt.plot(self.df[x_col], self.df[y_col], 
                marker='o', 
                linestyle='-', 
                linewidth=2, 
                markersize=6,
                color='#2E86AB',
                label=y_col)
        
        # 设置图表样式
        title=f"{x_col}-{y_col} Trend Chart"
        plt.title(title, fontsize=14, fontweight='bold', pad=20)
        
        # 添加统计信息注释框
        stats_text = (f"Pearson:  r = {self.pearson_corr:.4f}, p  = {self.pearson_p:.4f}\n"
                    f"Spearman: r = {self.spearman_corr:.4f}, p = {self.spearman_p:.4f}\n"
        )
        plt.annotate(stats_text, 
                xy=(0.02, 0.98), 
                xycoords='axes fraction',
                bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", alpha=0.8),
                fontsize=10, 
                ha='left', 
                va='top')

        plt.xlabel(x_col, fontsize=12)
        plt.ylabel(y_col, fontsize=12)
        plt.grid(True, alpha=0.3, linestyle='--')
        plt.legend()

        # 美化坐标轴
        plt.tight_layout()
        
        # 显示图表
        plt.savefig(f'{self.csv_file}_1.png', dpi=300, bbox_inches='tight') # 保存为PNG文件

        plt.close() # 释放内存
 
    def plot(self, x_col, y_col):
        if not self.is_linear_relationship(x_col, y_col):
            logger.error("❌ 数据不呈现线性关系，无法绘制趋势图")
            return False
        try:
            self.plot_data_trend(x_col, y_col)
            self.plot_linear_relationship(x_col, y_col)
        except Exception as e:
            logger.error(f"❌ 绘图过程中出现错误: {e}")
            return False
        return True


if __name__ == "__main__":
    analyzer = DataAnalyzer("data/4_data_20260517_165503.csv")
    analyzer.plot(y_col='Steps', x_col='Force_Value')

