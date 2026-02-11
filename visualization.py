import matplotlib.pyplot as plt
import seaborn as sns
import os
from config import OUTPUT_DIR, ANALYSIS_REPORT

def generate_visualizations(analysis_result):
    """生成分析图表并嵌入HTML报告"""
    if "error" in analysis_result:
        return
    
    df = analysis_result["raw_data"]
    summary = analysis_result["summary"]
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    # 1. 文件大小分布
    sns.histplot(df['file_size_kb'], kde=True, ax=axes[0], color='skyblue')
    axes[0].axvline(summary["平均文件大小(KB)"], color='red', linestyle='--', label='均值')
    axes[0].set_title('瓦片文件大小分布 (KB)')
    axes[0].set_xlabel('文件大小')
    axes[0].legend()
    
    # 2. 瓦片空间分布热力图（简化版：按x/y坐标密度）
    heatmap_data = df.groupby(['x', 'y']).size().unstack(fill_value=0)
    sns.heatmap(heatmap_data, cmap='YlGnBu', ax=axes[1])
    axes[1].set_title('瓦片空间分布密度')
    axes[1].set_xlabel('X坐标')
    axes[1].set_ylabel('Y坐标')
    
    plt.tight_layout()
    chart_path = os.path.join(OUTPUT_DIR, "analysis_chart.png")
    plt.savefig(chart_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    # 生成HTML报告（简洁专业，适合放入简历附件）
    html = f"""
    <html><head><title>天地图数据分析报告</title>
    <style>body{{font-family:Arial,sans-serif;line-height:1.6;max-width:900px;margin:20px auto}}
    .summary{{background:#f0f8ff;padding:15px;border-radius:8px;margin:20px 0}}
    .insight{{background:#fffacd;padding:10px;margin:10px 0;border-left:4px solid #ffc107}}
    h1{{color:#1a5276;text-align:center}}
    </style></head><body>
    <h1>📍 天地图瓦片数据分析报告</h1>
    <div class="summary"><h2>📊 核心指标</h2><ul>
    """
    for k, v in summary.items():
        html += f"<li><strong>{k}:</strong> {v}</li>"
    html += "</ul></div><h2>💡 洞察与建议</h2>"
    for insight in analysis_result["insights"]:
        html += f'<div class="insight">{insight}</div>'
    html += f'<h2>📈 可视化分析</h2><img src="analysis_chart.png" width="100%">'
    html += f"<p style='color:#7f8c8d;text-align:center;margin-top:30px'>报告生成时间: {summary['分析时间']} | 项目：地理空间数据简易分析（Python+Pandas）</p></body></html>"
    
    with open(ANALYSIS_REPORT, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"✅ 分析报告已生成: {ANALYSIS_REPORT}")