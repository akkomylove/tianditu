import os
import json
import logging
# ========== 新增导入 ==========
from db_utils import db

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("visualization")

# 保留原有辅助函数（format_coord_value/generate_star_rating/generate_progress_bar/generate_poi_chart）
def format_coord_value(value, default=0.0):
    try:
        float_value = float(value) if value is not None and value != '' else default
        return f"{float_value:.6f}"
    except (ValueError, TypeError):
        return f"{default:.6f}"

def generate_star_rating(score):
    try:
        score = float(score)
    except (ValueError, TypeError):
        score = 0.0
    star_score = min(5, max(0, score / 2))
    full_stars = int(star_score)
    half_star = 1 if (star_score - full_stars) >= 0.5 else 0
    empty_stars = 5 - full_stars - half_star
    star_html = "★" * full_stars + ("☆"[:half_star] if half_star else "") + "☆" * empty_stars
    return f"""
    <span style="color: #ffc107; font-size: 18px; font-weight: bold;">{star_html}</span>
    <span style="margin-left: 8px; color: #666;">{score:.1f}分</span>
    """

def generate_progress_bar(score):
    try:
        score = float(score)
    except (ValueError, TypeError):
        score = 0.0
    percentage = min(100, max(0, score * 10))
    color = "#28a745" if score >= 8 else "#ffc107" if score >= 5 else "#dc3545"
    return f"""
    <div style="width: 200px; height: 10px; background: #e9ecef; border-radius: 5px; overflow: hidden; display: inline-block; vertical-align: middle;">
        <div style="width: {percentage}%; height: 100%; background: {color};"></div>
    </div>
    <span style="margin-left: 8px; color: #333;">{score:.1f}分</span>
    """

def generate_poi_chart(all_poi_detail):
    """扩展POI图表：支持6大类分析数据"""
    def is_valid_poi_data(data):
        return isinstance(data, dict) and all(isinstance(v, (int, float)) for v in data.values())
    
    # 筛选有效数据
    valid_data = {}
    for category, detail in all_poi_detail.items():
        if is_valid_poi_data(detail):
            # 取每个类别前5个POI类型（避免图表过于拥挤）
            top5 = dict(sorted(detail.items(), key=lambda x: x[1], reverse=True)[:5])
            valid_data[category] = top5
    
    if not valid_data:
        return "<p style='color: #666; margin: 20px 0;'>⚠️ 无有效POI数据，无法生成图表</p>"
    
    # 构造图表数据
    all_labels = []
    all_datasets = []
    colors = [
        "rgba(54, 162, 235, 0.7)", "rgba(255, 159, 64, 0.7)",
        "rgba(75, 192, 192, 0.7)", "rgba(153, 102, 255, 0.7)",
        "rgba(255, 99, 132, 0.7)", "rgba(201, 203, 207, 0.7)"
    ]
    category_names = {
        "traffic": "交通", "life": "生活服务", "commercial": "商业",
        "education": "教育", "medical": "医疗", "culture": "文化"
    }
    
    for i, (category, detail) in enumerate(valid_data.items()):
        labels = list(detail.keys())
        values = list(detail.values())
        # 补充标签到总列表（去重）
        for label in labels:
            if label not in all_labels:
                all_labels.append(label)
        # 构造数据集
        all_datasets.append({
            "label": f"{category_names.get(category, category)}POI数量",
            "data": [detail.get(l, 0) for l in all_labels],
            "backgroundColor": colors[i % len(colors)],
            "borderColor": colors[i % len(colors)].replace("0.7", "1"),
            "borderWidth": 1
        })
    
    chart_html = f"""
    <div style="margin: 20px 0; padding: 20px; background: #fff; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
        <h4 style="margin-top: 0; color: #2c3e50;">6大类POI数量对比</h4>
        <canvas id="poiChart" width="600" height="300"></canvas>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <script>
            const ctx = document.getElementById('poiChart').getContext('2d');
            new Chart(ctx, {{
                type: 'bar',
                data: {{
                    labels: {json.dumps(all_labels)},
                    datasets: {json.dumps(all_datasets)}
                }},
                options: {{
                    responsive: true,
                    scales: {{
                        y: {{beginAtZero: true, title: {{display: true, text: 'POI数量'}}}},
                        x: {{title: {{display: true, text: 'POI类型'}}}}
                    }},
                    plugins: {{legend: {{position: 'bottom'}}}}
                }}
            }});
        </script>
    </div>
    """
    return chart_html

def generate_report(analysis_result, place_name=None, tile_type=None, zoom_level=None, bounds=None, output_path=None, operation_id=None):
    """
    生成可视化报告（适配output目录+新增6大类分析）
    :return: 成功返回True，失败返回False
    """
    try:
        # 参数默认值（保持原有）
        place_name = place_name or analysis_result.get("basic_info", {}).get("place_name", "未知地址")
        tile_type = tile_type or analysis_result.get("basic_info", {}).get("tile_type", "未知瓦片类型")
        zoom_level = zoom_level or analysis_result.get("basic_info", {}).get("zoom_level", 12)
        bounds = bounds or analysis_result.get("basic_info", {}).get("bounds", {})
        
        # 改造：适配output目录（优先使用传入的output_path，确保路径在output下）
        if not output_path:
            # 自动生成output目录下的报告路径（基于operation_id）
            if operation_id:
                output_dir = os.path.join("output", operation_id)
                os.makedirs(output_dir, exist_ok=True)
                output_path = os.path.join(output_dir, "analysis_report.html")
            else:
                from config import ANALYSIS_REPORT
                output_path = ANALYSIS_REPORT
        
        # ========== 核心修改1：提取6大类分析结果 ==========
        traffic_analysis = analysis_result.get("traffic_analysis", {})
        life_analysis = analysis_result.get("life_analysis", {})
        commercial_analysis = analysis_result.get("commercial_analysis", {})
        education_analysis = analysis_result.get("education_analysis", {})
        medical_analysis = analysis_result.get("medical_analysis", {})
        culture_analysis = analysis_result.get("culture_analysis", {})
        insights = analysis_result.get("insights", [])
        
        # ========== 核心修改2：生成6大类可视化组件 ==========
        # 交通
        traffic_score = traffic_analysis.get("traffic_convenience_score", 0)
        traffic_rating = generate_star_rating(traffic_score)
        traffic_progress = generate_progress_bar(traffic_score)
        # 生活服务
        life_score = life_analysis.get("life_convenience_score", 0)
        life_rating = generate_star_rating(life_score)
        life_progress = generate_progress_bar(life_score)
        # 商业
        commercial_score = commercial_analysis.get("commercial_activity_score", 0)
        commercial_rating = generate_star_rating(commercial_score)
        commercial_progress = generate_progress_bar(commercial_score)
        # 教育
        education_score = education_analysis.get("education_support_score", 0)
        education_rating = generate_star_rating(education_score)
        education_progress = generate_progress_bar(education_score)
        # 医疗
        medical_score = medical_analysis.get("medical_support_score", 0)
        medical_rating = generate_star_rating(medical_score)
        medical_progress = generate_progress_bar(medical_score)
        # 文化
        culture_score = culture_analysis.get("culture_feature_score", 0)
        culture_rating = generate_star_rating(culture_score)
        culture_progress = generate_progress_bar(culture_score)
        
        # 构造6大类POI详情（用于图表）
        all_poi_detail = {
            "traffic": traffic_analysis.get("traffic_poi_detail", {}),
            "life": life_analysis.get("life_poi_detail", {}),
            "commercial": commercial_analysis.get("commercial_poi_detail", {}),
            "education": education_analysis.get("education_poi_detail", {}),
            "medical": medical_analysis.get("medical_poi_detail", {}),
            "culture": culture_analysis.get("culture_poi_detail", {})
        }
        poi_chart = generate_poi_chart(all_poi_detail)
        
        # 处理分析洞察
        insights_html = ""
        for insight in insights:
            insights_html += f"<li style='margin: 8px 0; line-height: 1.6;'>{insight}</li>"
        if not insights_html:
            insights_html = "<li style='color: #666;'>暂无分析洞察</li>"
        
        # 坐标格式化（保持原有）
        min_lon = format_coord_value(bounds.get('min_lon'))
        max_lon = format_coord_value(bounds.get('max_lon'))
        min_lat = format_coord_value(bounds.get('min_lat'))
        max_lat = format_coord_value(bounds.get('max_lat'))
        
        # ========== 核心修改3：扩展HTML模板（新增4大类分析卡片） ==========
        html_template = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>天地图综合分析报告 - {place_name}</title>
    <style>
        * {{margin: 0; padding: 0; box-sizing: border-box;}}
        body {{font-family: "Microsoft YaHei", Arial, sans-serif; background: #f5f7fa; color: #333; line-height: 1.6; padding: 20px;}}
        .container {{max-width: 1200px; margin: 0 auto; background: #fff; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.08); overflow: hidden;}}
        .header {{background: linear-gradient(135deg, #4299e1, #38b2ac); color: #fff; padding: 30px 20px; text-align: center;}}
        .header h1 {{font-size: 24px; margin-bottom: 10px;}}
        .header p {{font-size: 16px; opacity: 0.9;}}
        .section {{padding: 20px; border-bottom: 1px solid #f0f0f0;}}
        .section:last-child {{border-bottom: none;}}
        .section h2 {{color: #2c3e50; font-size: 18px; margin-bottom: 15px; padding-bottom: 8px; border-bottom: 2px solid #e9ecef;}}
        .info-card {{display: flex; flex-wrap: wrap; gap: 15px; margin: 10px 0;}}
        .card-item {{flex: 1; min-width: 200px; padding: 15px; background: #f8f9fa; border-radius: 8px; border-left: 4px solid #4299e1;}}
        .card-item.life {{border-left-color: #ff9f43;}}
        .card-item.commercial {{border-left-color: #48bb78;}}
        .card-item.education {{border-left-color: #9f7aea;}}
        .card-item.medical {{border-left-color: #e53e3e;}}
        .card-item.culture {{border-left-color: #38b2ac;}}
        .card-item h3 {{font-size: 16px; color: #2c3e50; margin-bottom: 10px;}}
        .card-item p {{margin: 5px 0;}}
        .key {{color: #666; display: inline-block; width: 100px;}}
        .value {{color: #2c3e50; font-weight: bold;}}
        .insights {{background: #fef7fb; padding: 15px; border-radius: 8px; margin: 15px 0;}}
        .insights h3 {{color: #e53e3e; font-size: 16px; margin-bottom: 10px;}}
        .insights ul {{padding-left: 20px;}}
        .map-container {{text-align: center; margin: 20px 0;}}
        .map-container img {{max-width: 100%; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);}}
        .footer {{text-align: center; padding: 20px; color: #666; font-size: 12px; background: #f8f9fa;}}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📍 天地图6大类综合分析报告</h1>
            <p>查询地址：{place_name} | 瓦片类型：{tile_type} | 缩放等级：{zoom_level}</p>
            <p style="font-size: 14px; opacity: 0.8; margin-top: 8px;">
                地理边界：经度 {min_lon}~{max_lon}，纬度 {min_lat}~{max_lat}
            </p>
        </div>
        <div class="section">
            <h2>📊 核心分析结果</h2>
            <div class="info-card">
                <!-- 交通分析卡片 -->
                <div class="card-item">
                    <h3>🚗 交通分析</h3>
                    <p><span class="key">总POI数：</span><span class="value">{traffic_analysis.get('total_traffic_poi_count', '未知')}</span></p>
                    <p><span class="key">POI密度：</span><span class="value">{traffic_analysis.get('traffic_density_per_sqkm', '未知')} 个/平方公里</span></p>
                    <p><span class="key">便利度：</span>{traffic_progress}</p>
                    <p style="margin-top: 10px;">{traffic_rating}</p>
                </div>
                <!-- 生活服务分析卡片 -->
                <div class="card-item life">
                    <h3>🛒 生活服务</h3>
                    <p><span class="key">总POI数：</span><span class="value">{life_analysis.get('total_life_poi_count', '未知')}</span></p>
                    <p><span class="key">POI密度：</span><span class="value">{life_analysis.get('life_density_per_sqkm', '未知')} 个/平方公里</span></p>
                    <p><span class="key">便利度：</span>{life_progress}</p>
                    <p style="margin-top: 10px;">{life_rating}</p>
                </div>
                <!-- 商业分析卡片 -->
                <div class="card-item commercial">
                    <h3>🏬 商业设施</h3>
                    <p><span class="key">总POI数：</span><span class="value">{commercial_analysis.get('total_commercial_poi_count', '未知')}</span></p>
                    <p><span class="key">POI密度：</span><span class="value">{commercial_analysis.get('commercial_density_per_sqkm', '未知')} 个/平方公里</span></p>
                    <p><span class="key">活跃度：</span>{commercial_progress}</p>
                    <p style="margin-top: 10px;">{commercial_rating}</p>
                </div>
            </div>
            <div class="info-card" style="margin-top: 20px;">
                <!-- 教育分析卡片 -->
                <div class="card-item education">
                    <h3>🏫 教育设施</h3>
                    <p><span class="key">总POI数：</span><span class="value">{education_analysis.get('total_education_poi_count', '未知')}</span></p>
                    <p><span class="key">POI密度：</span><span class="value">{education_analysis.get('education_density_per_sqkm', '未知')} 个/平方公里</span></p>
                    <p><span class="key">配套分：</span>{education_progress}</p>
                    <p style="margin-top: 10px;">{education_rating}</p>
                </div>
                <!-- 医疗分析卡片 -->
                <div class="card-item medical">
                    <h3>🏥 医疗设施</h3>
                    <p><span class="key">总POI数：</span><span class="value">{medical_analysis.get('total_medical_poi_count', '未知')}</span></p>
                    <p><span class="key">POI密度：</span><span class="value">{medical_analysis.get('medical_density_per_sqkm', '未知')} 个/平方公里</span></p>
                    <p><span class="key">配套分：</span>{medical_progress}</p>
                    <p style="margin-top: 10px;">{medical_rating}</p>
                </div>
                <!-- 文化分析卡片 -->
                <div class="card-item culture">
                    <h3>🎨 文化分析</h3>
                    <p><span class="key">总POI数：</span><span class="value">{culture_analysis.get('total_culture_poi_count', '未知')}</span></p>
                    <p><span class="key">POI密度：</span><span class="value">{culture_analysis.get('culture_density_per_sqkm', '未知')} 个/平方公里</span></p>
                    <p><span class="key">特色分：</span>{culture_progress}</p>
                    <p style="margin-top: 10px;">{culture_rating}</p>
                </div>
            </div>
            {poi_chart}
            <div class="insights">
                <h3>💡 综合分析洞察</h3>
                <ul>{insights_html}</ul>
            </div>
        </div>
        <div class="section">
            <h2>🖼️ 拼接地图预览</h2>
            <div class="map-container">
                <!-- 适配output目录的地图路径 -->
                <img src="merged_map.jpg" alt="{place_name}地图">
                <p style="margin-top: 10px; color: #666; font-size: 14px;">
                    地图文件路径：{os.path.join(os.path.dirname(output_path), 'merged_map.jpg')}
                </p>
            </div>
        </div>
        <div class="footer">
            <p>报告生成时间：{db.get_current_time()} | 天地图综合分析工具 © 2026</p>
            <p style="margin-top: 5px;">数据来源：天地图瓦片、高德地图POI接口 | 输出目录：{os.path.dirname(output_path)}</p>
        </div>
    </div>
</body>
</html>
        """
        
        # 保存报告（确保output目录存在）
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_template)
        logger.info(f"报告保存成功：{output_path}")
        
        # ========== 保留原有数据库写入逻辑 ==========
        if operation_id:
            logger.info(f"写入报告信息到数据库（operation_id：{operation_id}）")
            current_time = db.get_current_time()
            # 构造插入参数
            insert_params = (
                operation_id,
                os.path.abspath(output_path),
                "success",
                current_time,
                current_time
            )
            # 执行插入
            insert_sql = """
            INSERT INTO reports 
            (operation_id, report_path, generate_status, create_time, update_time)
            VALUES (?, ?, ?, ?, ?)
            """
            insert_result = db.execute(insert_sql, insert_params, commit=True)
            if insert_result is None:
                logger.warning("报告信息写入数据库失败（文件已保存）")
            else:
                logger.info("报告信息写入数据库成功")
            
            # 更新分析结果表的洞察
            update_sql = """
            UPDATE analysis_results 
            SET insights = ?, update_time = ? 
            WHERE operation_id = ?
            """
            update_result = db.execute(update_sql, (json.dumps(insights), current_time, operation_id), commit=True)
            if update_result is None:
                logger.warning("分析洞察更新到数据库失败")
            else:
                logger.info("分析洞察更新到数据库成功")
        
        return True
    except Exception as e:
        logger.error(f"报告生成失败：{str(e)}", exc_info=True)
        # 写入失败状态到报告表
        if operation_id:
            current_time = db.get_current_time()
            insert_sql = """
            INSERT INTO reports 
            (operation_id, report_path, generate_status, create_time, update_time)
            VALUES (?, ?, ?, ?, ?)
            """
            db.execute(insert_sql, (operation_id, output_path or "", "failed", current_time, current_time), commit=True)
        return False

# 测试用例（适配output目录）
if __name__ == "__main__":
    test_analysis = {
        "basic_info": {"place_name": "北京中关村", "tile_type": "影像图", "zoom_level": 15, "bounds": {"min_lon": 116.30, "max_lon": 116.33, "min_lat": 39.97, "max_lat": 40.00}},
        "traffic_analysis": {"total_traffic_poi_count": 28, "traffic_poi_detail": {"公交站": 12, "地铁站": 8, "停车场": 6, "加油站": 2}, "traffic_density_per_sqkm": 28.28, "traffic_convenience_score": 8.5},
        "life_analysis": {"total_life_poi_count": 45, "life_poi_detail": {"超市": 15, "便利店": 20, "餐厅": 10}, "life_density_per_sqkm": 45.45, "life_convenience_score": 9.0},
        "commercial_analysis": {"total_commercial_poi_count": 32, "commercial_poi_detail": {"商场": 5, "写字楼": 18, "银行": 9}, "commercial_density_per_sqkm": 32.32, "commercial_activity_score": 8.2},
        "education_analysis": {"total_education_poi_count": 18, "education_poi_detail": {"小学": 6, "中学": 4, "大学": 8}, "education_density_per_sqkm": 18.18, "education_support_score": 7.8},
        "medical_analysis": {"total_medical_poi_count": 12, "medical_poi_detail": {"医院": 4, "诊所": 6, "药店": 2}, "medical_density_per_sqkm": 12.12, "medical_support_score": 6.5},
        "culture_analysis": {"total_culture_poi_count": 7, "culture_poi_detail": {"博物馆": 1, "图书馆": 2, "文创园区": 4}, "culture_density_per_sqkm": 7.07, "culture_feature_score": 4.2},
        "insights": [
            "北京中关村交通便利度极高（8.5分），生活配套完善（9.0分）",
            "商业活跃度高（8.2分），教育资源丰富（7.8分）",
            "医疗配套一般（6.5分），文化特色较弱（4.2分）",
            "综合配套评分8.0分，属于优质配套区域"
        ]
    }
    # 测试：生成output目录下的报告
    test_operation_id = "20260213_163000_test"
    generate_report(
        test_analysis,
        place_name="北京中关村",
        tile_type="影像图",
        zoom_level=15,
        bounds={"min_lon": 116.30, "max_lon": 116.33, "min_lat": 39.97, "max_lat": 40.00},
        output_path=os.path.join("output", test_operation_id, "analysis_report.html"),
        operation_id=test_operation_id
    )
