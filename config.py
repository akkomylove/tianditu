import os
from dotenv import load_dotenv

# 优先加载项目根目录的 .env 文件
load_dotenv()

# 严格校验密钥（无密钥立即报错，避免泄露风险）
TIANDITU_KEY = os.getenv("TIANDITU_KEY")
if not TIANDITU_KEY or TIANDITU_KEY == "your_actual_key_here":
    raise EnvironmentError(
        "❌ 未配置有效天地图密钥！\n"
        "👉 请执行：cp .env.example .env && 编辑 .env 填入真实密钥\n"
        "🔒 安全提示：.env 已加入 .gitignore，请勿提交到代码仓库！"
    )

# 安全构建API URL
TIANDITU_URL = f"http://t0.tianditu.gov.cn/DataServer?T=vec_w&x={{x}}&y={{y}}&l={{z}}&tk={TIANDITU_KEY}"

# 从环境变量读取区域配置（带默认值）
BOUNDS = {
    "min_lon": float(os.getenv("MIN_LON", 116.30)),
    "max_lon": float(os.getenv("MAX_LON", 116.33)),
    "min_lat": float(os.getenv("MIN_LAT", 39.97)),
    "max_lat": float(os.getenv("MAX_LAT", 40.00))
}
ZOOM_LEVEL = int(os.getenv("ZOOM_LEVEL", 12))

# 输出路径（保持不变）
OUTPUT_DIR = "output"
TILE_DIR = f"{OUTPUT_DIR}/tiles"
MERGED_IMAGE = f"{OUTPUT_DIR}/merged_map.jpg"
ANALYSIS_REPORT = f"{OUTPUT_DIR}/analysis_report.html"