import os
from dotenv import load_dotenv

# 关键修复：指定.env的绝对路径+UTF-8编码，确保无论在哪运行都能读到
DOTENV_PATH = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path=DOTENV_PATH, encoding='utf-8')

# ===================== 基础密钥配置（保留原有逻辑，仅优化注释） =====================
# 严格校验天地图密钥（无密钥立即报错，避免泄露风险）
TIANDITU_KEY = os.getenv("TIANDITU_KEY")
if not TIANDITU_KEY or TIANDITU_KEY.strip() == "your_actual_key_here":
    raise EnvironmentError(
        "❌ 未配置有效天地图密钥！\n"
        "👉 请执行：cp .env.example .env && 编辑 .env 填入真实密钥\n"
        "🔒 安全提示：.env 已加入 .gitignore，请勿提交到代码仓库！"
    )

# ===================== 新增：瓦片类型配置（核心扩展） =====================
# 天地图瓦片类型映射（中文名称 → 天地图标识 → URL模板）
# 官方文档：https://www.tianditu.gov.cn/docs/jsdk/index.html#2
TIANDITU_TILE_TYPES = {
    "矢量图": {
        "code": "vec_w",       # 天地图矢量瓦片标识
        "url_template": f"https://t0.tianditu.gov.cn/DataServer?T=vec_w&x={{x}}&y={{y}}&l={{z}}&tk={TIANDITU_KEY.strip()}"
    },
    "影像图": {
        "code": "img_w",       # 天地图影像瓦片标识（卫星图）
        "url_template": f"https://t0.tianditu.gov.cn/DataServer?T=img_w&x={{x}}&y={{y}}&l={{z}}&tk={TIANDITU_KEY.strip()}"
    },
    "地形地图": {
        "code": "ter_w",       # 天地图地形瓦片标识
        "url_template": f"https://t0.tianditu.gov.cn/DataServer?T=ter_w&x={{x}}&y={{y}}&l={{z}}&tk={TIANDITU_KEY.strip()}"
    },
    "注记图层": {
        "code": "cva_w",       # 天地图注记瓦片标识（文字标注，需叠加在矢量/影像上）
        "url_template": f"https://t0.tianditu.gov.cn/DataServer?T=cva_w&x={{x}}&y={{y}}&l={{z}}&tk={TIANDITU_KEY.strip()}"
    }
}
# 默认瓦片类型（后续交互层可覆盖）
DEFAULT_TILE_TYPE = "矢量图"

# ===================== 缩放等级动态化配置（核心扩展） =====================
# 天地图缩放等级说明：1（全球）- 18（街区级），级数越高精度越高
ZOOM_LEVEL_RANGE = (1, 18)          # 缩放等级合法范围
DEFAULT_ZOOM_LEVEL = 12             # 默认缩放等级（城市级）
# 缩放等级精度说明（用于交互层提示用户）
ZOOM_LEVEL_DESC = {
    1-5: "全球/国家级别",
    6-10: "省级/市级概览",
    11-15: "城市/区县级别（常用）",
    16-18: "街区/门址级别（高精度）"
}

# ===================== 新增：用户地址存储（用于报告展示） =====================
# 初始值为空，后续由交互层（gui_main/main.py）赋值
USER_QUERY_ADDRESS = ""

# ===================== 原有输出路径配置（完全保留，确保兼容） =====================
OUTPUT_DIR = "output"
TILE_DIR = f"{OUTPUT_DIR}/tiles"
MERGED_IMAGE = f"{OUTPUT_DIR}/merged_map.jpg"
ANALYSIS_REPORT = f"{OUTPUT_DIR}/analysis_report.html"

# ===================== 原有区域边界配置（保留，可被动态地址覆盖） =====================
BOUNDS = {
    "min_lon": float(os.getenv("MIN_LON", 116.30)),
    "max_lon": float(os.getenv("MAX_LON", 116.33)),
    "min_lat": float(os.getenv("MIN_LAT", 39.97)),
    "max_lat": float(os.getenv("MAX_LAT", 40.00))
}