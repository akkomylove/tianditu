import os
from config import OUTPUT_DIR
from image_fetcher import fetch_tiles
from image_merger import merge_tiles
from data_analyzer import analyze_metadata
from visualization import generate_visualizations
from geocoder import get_location_bounds

def main():
    print("="*50)
    print("🌍 天地图智能区域查询系统")
    print("✨ 输入地名自动定位 | 支持中文 | 安全无密钥")
    print("="*50 + "\n")
    
    # ====== 新增：交互式区域设置 ======
    use_custom = input("🔍 是否自定义查询区域？(y/n，回车默认n): ").strip().lower()
    
    if use_custom == 'y':
        print("\n📌 提示：")
        print("   • 可输入: '北京中关村'、'上海外滩'、'深圳南山科技园'")
        print("   • 查询结果会缓存到 location_cache.json，下次更快")
        print("   • 如遇问题，可直接输入经纬度范围（示例: 116.30,116.33,39.97,40.00）\n")
        
        while True:
            query = input("📍 请输入地名或经纬度范围: ").strip()
            
            # 检查是否为经纬度格式（逗号分隔4个数字）
            if query.count(',') == 3 and all(part.replace('.','').replace('-','').isdigit() for part in query.split(',')):
                try:
                    min_lon, max_lon, min_lat, max_lat = map(float, query.split(','))
                    bounds = {
                        "min_lon": min_lon,
                        "max_lon": max_lon,
                        "min_lat": min_lat,
                        "max_lat": max_lat
                    }
                    print(f"✅ 已设置自定义范围: 经度[{min_lon}~{max_lon}] 纬度[{min_lat}~{max_lat}]")
                    # 动态覆盖config中的BOUNDS（安全：仅本次运行生效）
                    import config
                    config.BOUNDS = bounds
                    break
                except:
                    print("❌ 格式错误！请按示例输入: min_lon,max_lon,min_lat,max_lat")
                    continue
            
            # 尝试地理编码
            bounds, msg = get_location_bounds(
                query, 
                user_agent=os.getenv("USER_AGENT", "tianditu_analyzer")
            )
            
            if bounds:
                # 动态覆盖config中的BOUNDS（关键！）
                import config
                config.BOUNDS = bounds
                break
            else:
                print(f"\n{msg}\n")
    else:
        print(f"⏭️  使用配置文件中的默认区域（中关村）\n")
    # ====== 区域设置结束 ======
    
    # 后续流程保持不变...
    metadata_df = fetch_tiles()  # 注意：需同步修改image_fetcher.py（见下文）
    # ...（其余代码不变）
    # 步骤1：下载瓦片（含元数据记录）
    metadata_df = fetch_tiles()
    
    # 步骤2：拼接地图（可选，依赖PIL）
    if not metadata_df.empty:
        merge_tiles(metadata_df)
    
    # 步骤3：数据分析（核心）
    analysis_result = analyze_metadata(metadata_df)
    
    # 步骤4：生成可视化报告
    generate_visualizations(analysis_result)
    
    print("\n" + "="*50)
    print("✅ 全流程执行完毕！")
    print(f"📁 输出目录: {os.path.abspath(OUTPUT_DIR)}")
    print("💡 面试提示：重点讲解 data_analyzer.py 中的异常检测逻辑与业务洞察")
    print("="*50)

if __name__ == "__main__":
    main()