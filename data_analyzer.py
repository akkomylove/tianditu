import pandas as pd
import numpy as np
from datetime import datetime
import matplotlib as mpl

mpl.rcParams['font.family'] = 'Microsoft YaHei'  # 核心：设置字体族
mpl.rcParams['axes.unicode_minus'] = False  # 解决负号显示异常



def analyze_metadata(metadata_df):
    """对瓦片元数据进行多维度分析"""
    if metadata_df.empty:
        return {"error": "无数据可分析"}
    
    # 基础统计
    total_tiles = len(metadata_df)
    avg_size = metadata_df['file_size_kb'].mean()
    size_std = metadata_df['file_size_kb'].std()
    
    # 空间分布分析
    lon_range = metadata_df['lon_center'].max() - metadata_df['lon_center'].min()
    lat_range = metadata_df['lat_center'].max() - metadata_df['lat_center'].min()
    
    # 异常检测（文件大小离群点）
    q1 = metadata_df['file_size_kb'].quantile(0.25)
    q3 = metadata_df['file_size_kb'].quantile(0.75)
    iqr = q3 - q1
    outliers = metadata_df[
        (metadata_df['file_size_kb'] < q1 - 1.5*iqr) | 
        (metadata_df['file_size_kb'] > q3 + 1.5*iqr)
    ]
    
    # 生成分析结论（面试时可重点讲解）
    insights = []
    if outliers.shape[0] > 0:
        insights.append(f"⚠️ 发现 {outliers.shape[0]} 个文件大小异常瓦片（可能加载失败）")
    if avg_size < 10:
        insights.append("💡 瓦片平均体积较小，区域可能以文字/道路为主（建筑密集区通常>15KB）")
    insights.append(f"📍 覆盖区域约 {lon_range*111:.1f}km × {lat_range*111:.1f}km（粗略估算）")
    
    return {
        "summary": {
            "总瓦片数": total_tiles,
            "平均文件大小(KB)": round(avg_size, 2),
            "文件大小标准差": round(size_std, 2),
            "经度跨度(度)": round(lon_range, 4),
            "纬度跨度(度)": round(lat_range, 4),
            "分析时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        },
        "outliers_count": outliers.shape[0],
        "insights": insights,
        "raw_data": metadata_df  # 供可视化模块使用
    }