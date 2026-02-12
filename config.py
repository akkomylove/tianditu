import os
from dotenv import load_dotenv

# 关键修复：指定.env的绝对路径+UTF-8编码，确保无论在哪运行都能读到
DOTENV_PATH = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path=DOTENV_PATH, encoding='utf-8')

# ===================== 天地图密钥配置（保留原有逻辑） =====================
TIANDITU_KEY = os.getenv("TIANDITU_KEY")
if not TIANDITU_KEY or TIANDITU_KEY.strip() == "your_actual_key_here":
    raise EnvironmentError(
        "❌ 未配置有效天地图密钥！\n"
        "👉 请执行：cp .env.example .env && 编辑 .env 填入真实密钥\n"
        "🔒 安全提示：.env 已加入 .gitignore，请勿提交到代码仓库！"
    )

# ===================== 新增：高德API配置（核心修改） =====================
# 高德Web服务API Key（从.env读取）
AMAP_KEY = os.getenv("AMAP_KEY")
# 高德API URL模板（统一管理，方便后续修改）
AMAP_POI_URL = "https://restapi.amap.com/v3/place/polygon"
AMAP_GEOCODE_URL = "https://restapi.amap.com/v3/geocode/geo"

# 高德Key校验（非强制，无Key时触发降级分析）
if not AMAP_KEY or AMAP_KEY.strip() == "your_amap_key_here":
    print("⚠️ 未配置有效高德API Key，将启用降级分析（无POI数据）！")
    print("👉 请在.env文件中添加：AMAP_KEY=你的高德Web服务API Key")

# ===================== 原有瓦片类型/缩放等级配置（保留） =====================
TIANDITU_TILE_TYPES = {
    "矢量图": {
        "code": "vec_w",
        "url_template": f"https://t0.tianditu.gov.cn/DataServer?T=vec_w&x={{x}}&y={{y}}&l={{z}}&tk={TIANDITU_KEY.strip()}"
    },
    "影像图": {
        "code": "img_w",
        "url_template": f"https://t0.tianditu.gov.cn/DataServer?T=img_w&x={{x}}&y={{y}}&l={{z}}&tk={TIANDITU_KEY.strip()}"
    },
    "地形地图": {
        "code": "ter_w",
        "url_template": f"https://t0.tianditu.gov.cn/DataServer?T=ter_w&x={{x}}&y={{y}}&l={{z}}&tk={TIANDITU_KEY.strip()}"
    },
    "注记图层": {
        "code": "cva_w",
        "url_template": f"https://t0.tianditu.gov.cn/DataServer?T=cva_w&x={{x}}&y={{y}}&l={{z}}&tk={TIANDITU_KEY.strip()}"
    }
}
DEFAULT_TILE_TYPE = "矢量图"

ZOOM_LEVEL_RANGE = range(1, 19)
DEFAULT_ZOOM_LEVEL = 12
ZOOM_LEVEL_DESC = {
    "1-5": "全球/国家级别",
    "6-10": "省级/市级概览",
    "11-15": "城市/区县级别（常用）",
    "16-18": "街区/门址级别（高精度）"
}

USER_QUERY_ADDRESS = ""

# ===================== 原有输出路径配置（保留） =====================
OUTPUT_DIR = "output"
TILE_DIR = f"{OUTPUT_DIR}/tiles"
MERGED_IMAGE = f"{OUTPUT_DIR}/merged_map.jpg"
ANALYSIS_REPORT = f"{OUTPUT_DIR}/analysis_report.html"

BOUNDS = {
    "min_lon": float(os.getenv("MIN_LON", 116.30)),
    "max_lon": float(os.getenv("MAX_LON", 116.33)),
    "min_lat": float(os.getenv("MIN_LAT", 39.97)),
    "max_lat": float(os.getenv("MAX_LAT", 40.00))
}

# ===================== 新增：数据库配置（核心修复） =====================
# 数据库类型（默认SQLite）
DB_TYPE = os.getenv("DB_TYPE", "sqlite")
# SQLite配置（默认存储在项目根目录）
DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(__file__), "tianditu_analysis.db"))
# 数据库连接超时（秒）
DB_TIMEOUT = int(os.getenv("DB_TIMEOUT", 30))

# MySQL/PostgreSQL配置（后续迁移用，当前注释）
# DB_HOST = os.getenv("DB_HOST", "localhost")
# DB_PORT = int(os.getenv("DB_PORT", 3306))
# DB_USER = os.getenv("DB_USER", "root")
# DB_PWD = os.getenv("DB_PWD", "")
# DB_NAME = os.getenv("DB_NAME", "tianditu_analysis")