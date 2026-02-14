<<<<<<< HEAD
import requests
import json
import logging
import math
from functools import lru_cache
from config import AMAP_KEY
# ========== 新增导入 ==========
from db_utils import db
from data_validator import validate_numeric
from db_utils import logger

# 配置日志（优化：增加详细度，区分模块）
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
)
logger = logging.getLogger("data_analyzer")

# ========== 核心扩展1：新增4大类POI，扩展分析广度 ==========
# 原有POI分类（保留）
TRAFFIC_POI_TYPES = {
    "公交站": "150500",
    "地铁站": "150600",
    "停车场": "150900",
    "加油站": "150701",
    "道路服务区": "150702"
}
CULTURE_POI_TYPES = {
    "博物馆": "080100",
    "图书馆": "080200",
    "文化馆": "080300",
    "文物古迹": "080400",
    "美术馆": "080500",
    "文创园区": "100110"
}

# 新增：生活服务POI（贴近日常需求）
LIFE_POI_TYPES = {
    "超市": "090100",
    "便利店": "090101",
    "菜市场": "090102",
    "药店": "090201",
    "快递网点": "090800",
    "银行": "140300"
}
# 新增：商业设施POI（商业价值分析）
COMMERCIAL_POI_TYPES = {
    "购物中心": "090400",
    "百货商场": "090401",
    "餐饮场所": "090500",
    "酒店民宿": "140000",
    "写字楼": "120200"
}
# 新增：教育设施POI（民生配套分析）
EDUCATION_POI_TYPES = {
    "幼儿园": "140101",
    "小学": "140100",
    "中学": "140200",
    "大学": "140300",
    "培训机构": "140400"
}
# 新增：医疗设施POI（健康配套分析）
MEDICAL_POI_TYPES = {
    "综合医院": "150200",
    "专科医院": "150201",
    "社区卫生服务中心": "150202",
    "诊所": "150203",
    "急救中心": "150204"
}

# ========== 核心扩展2：优化POI数量获取（分页+缓存，提升数据准确性） ==========
@lru_cache(maxsize=1000)  # 缓存机制：避免重复调用API，节省额度
def get_poi_count(min_lon, max_lon, min_lat, max_lat, poi_type_code):
    """
    优化：处理高德API分页，获取真实总数量（原逻辑仅取第一页count，超1000条会失真）
    :return: 真实POI总数量
    """
    if not AMAP_KEY:
        logger.warning("高德API Key未配置，返回POI数量为0")
        return 0
    
    base_url = "https://restapi.amap.com/v3/place/polygon"
    page = 1
    total_count = 0
    max_page = 100  # 高德API最大支持100页（10000条），避免无限循环
    
    try:
        while page <= max_page:
            params = {
                "key": AMAP_KEY,
                "polygon": f"{min_lon},{min_lat}|{max_lon},{max_lat}",
                "types": poi_type_code,
                "output": "json",
                "offset": 100,  # 每页最多100条，提升查询效率
                "page": page
            }
            response = requests.get(base_url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            # 首次请求获取总页数
            if page == 1:
                total_count = int(data.get("count", 0))
                if total_count == 0:
                    break  # 无数据直接返回
                # 计算总页数（向上取整）
                max_page = min(math.ceil(total_count / 100), 100)  # 限制最大100页
                logger.debug(f"POI类型{poi_type_code}：总数量{total_count}，需查询{max_page}页")
            
            page += 1
        
        return total_count
    except Exception as e:
        logger.warning(f"获取POI数量失败（类型码：{poi_type_code}）：{str(e)}")
        return 0

def calculate_density(poi_count: int, min_lon: float, max_lon: float, min_lat: float, max_lat: float) -> float:
    """
    计算POI密度（单位：个/平方公里）
    核心逻辑：
    1. 基于经纬度计算地理区域的球面面积（平方公里）
    2. 密度 = POI总数 / 区域面积（处理面积为0的边界情况）
    """
    if poi_count == 0:
        return 0.0
    
    # 地球半径（公里）
    EARTH_RADIUS = 6371.0
    # 经纬度转弧度
    min_lon_rad = math.radians(min_lon)
    max_lon_rad = math.radians(max_lon)
    min_lat_rad = math.radians(min_lat)
    max_lat_rad = math.radians(max_lat)
    
    try:
        # 球面矩形面积计算公式（哈维正弦公式简化版）
        # 面积 = R² * |(lon2-lon1) * (sin(lat2)-sin(lat1))|
        lon_diff = max_lon_rad - min_lon_rad
        lat_sin_diff = math.sin(max_lat_rad) - math.sin(min_lat_rad)
        area_sqkm = (EARTH_RADIUS **2) * abs(lon_diff * lat_sin_diff)
        
        # 边界处理：面积为0（经纬度范围无效）
        if area_sqkm <= 1e-6:  # 小于1平方米视为无效区域
            logger.warning(f"计算密度时区域面积为0（经纬度范围：{min_lon},{max_lon},{min_lat},{max_lat}）")
            return 0.0
        
        # 计算密度并保留2位小数
        density = round(poi_count / area_sqkm, 2)
        return density
    except Exception as e:
        logger.warning(f"计算POI密度失败：{str(e)}")
        return 0.0

# ========== 核心扩展3：新增分析维度（占比+集中度+交叉关联） ==========
def calculate_type_ratio(poi_detail: dict) -> dict:
    """计算各类POI占比（深度分析：识别主导类型）"""
    total = sum(poi_detail.values())
    if total == 0:
        return {k: 0.0 for k in poi_detail.keys()}
    return {k: round((v / total) * 100, 1) for k, v in poi_detail.items()}

def calculate_concentration(poi_detail: dict) -> float:
    """计算POI集中度（标准差越小越均匀，越大越集中于某类）"""
    values = list(poi_detail.values())
    if len(values) < 2 or sum(values) == 0:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum([(v - mean) ** 2 for v in values]) / len(values)
    return round(math.sqrt(variance), 2)

def correlate_poi_densities(density1: float, density2: float) -> float:
    """计算两类POI密度的相关系数（交叉分析：判断配套关联性）"""
    if density1 == 0 or density2 == 0:
        return 0.0
    # 简化相关系数计算（0-1之间，越接近1关联性越强）
    return round(min(density1, density2) / max(density1, density2), 2)

# ========== 核心扩展4：新增4类POI分析函数（保持原有接口风格） ==========
def analyze_life(min_lon, max_lon, min_lat, max_lat, operation_id=None) -> dict:
    """生活服务POI分析（新增）"""
    logger.info("开始生活服务POI分析")
    life_poi_detail = {}
    total_life_poi = 0
    
    for poi_name, poi_code in LIFE_POI_TYPES.items():
        count = get_poi_count(min_lon, max_lon, min_lat, max_lat, poi_code)
        life_poi_detail[poi_name] = count
        total_life_poi += count
    
    # 计算核心指标（数量+密度+占比+集中度）
    life_density = calculate_density(total_life_poi, min_lon, max_lon, min_lat, max_lat)
    life_type_ratio = calculate_type_ratio(life_poi_detail)
    life_concentration = calculate_concentration(life_poi_detail)
    # 生活便利度评分（密度≥30→10分，线性插值）
    life_convenience_score = min(10.0, round(life_density * 0.33, 1))
    
    # 数值校验（新增）
    if not validate_numeric(life_convenience_score, 0, 10, "生活便利度评分"):
        life_convenience_score = 0.0
    if not validate_numeric(life_density, 0, None, "生活POI密度"):
        life_density = 0.0
    
    analysis_result = {
        "total_life_poi_count": total_life_poi,
        "life_poi_detail": life_poi_detail,
        "life_type_ratio": life_type_ratio,  # 新增：类型占比
        "life_concentration": life_concentration,  # 新增：集中度
        "life_density_per_sqkm": life_density,
        "life_convenience_score": life_convenience_score
    }
    
    # 暂存结果（用于后续合并）
    if operation_id:
        global _temp_analysis_results
        if operation_id not in _temp_analysis_results:
            _temp_analysis_results[operation_id] = {}
        _temp_analysis_results[operation_id]["life"] = analysis_result
    
    return analysis_result

def analyze_commercial(min_lon, max_lon, min_lat, max_lat, operation_id=None) -> dict:
    """商业设施POI分析（新增）"""
    logger.info("开始商业设施POI分析")
    commercial_poi_detail = {}
    total_commercial_poi = 0
    
    for poi_name, poi_code in COMMERCIAL_POI_TYPES.items():
        count = get_poi_count(min_lon, max_lon, min_lat, max_lat, poi_code)
        commercial_poi_detail[poi_name] = count
        total_commercial_poi += count
    
    commercial_density = calculate_density(total_commercial_poi, min_lon, max_lon, min_lat, max_lat)
    commercial_type_ratio = calculate_type_ratio(commercial_poi_detail)
    commercial_concentration = calculate_concentration(commercial_poi_detail)
    # 商业活跃度评分（密度≥20→10分，线性插值）
    commercial_activity_score = min(10.0, round(commercial_density * 0.5, 1))
    
    # 数值校验（新增）
    if not validate_numeric(commercial_activity_score, 0, 10, "商业活跃度评分"):
        commercial_activity_score = 0.0
    if not validate_numeric(commercial_density, 0, None, "商业POI密度"):
        commercial_density = 0.0
    
    analysis_result = {
        "total_commercial_poi_count": total_commercial_poi,
        "commercial_poi_detail": commercial_poi_detail,
        "commercial_type_ratio": commercial_type_ratio,
        "commercial_concentration": commercial_concentration,
        "commercial_density_per_sqkm": commercial_density,
        "commercial_activity_score": commercial_activity_score
    }
    
    if operation_id:
        global _temp_analysis_results
        if operation_id not in _temp_analysis_results:
            _temp_analysis_results[operation_id] = {}
        _temp_analysis_results[operation_id]["commercial"] = analysis_result
    
    return analysis_result

def analyze_education(min_lon, max_lon, min_lat, max_lat, operation_id=None) -> dict:
    """教育设施POI分析（新增）"""
    logger.info("开始教育设施POI分析")
    education_poi_detail = {}
    total_education_poi = 0
    
    for poi_name, poi_code in EDUCATION_POI_TYPES.items():
        count = get_poi_count(min_lon, max_lon, min_lat, max_lat, poi_code)
        education_poi_detail[poi_name] = count
        total_education_poi += count
    
    education_density = calculate_density(total_education_poi, min_lon, max_lon, min_lat, max_lat)
    education_type_ratio = calculate_type_ratio(education_poi_detail)
    education_concentration = calculate_concentration(education_poi_detail)
    # 教育配套评分（密度≥10→10分，线性插值）
    education_support_score = min(10.0, round(education_density * 1.0, 1))
    
    if not validate_numeric(education_support_score, 0, 10, "教育配套评分"):
        education_support_score = 0.0
    if not validate_numeric(education_density, 0, None, "教育POI密度"):
        education_density = 0.0
    
    analysis_result = {
        "total_education_poi_count": total_education_poi,
        "education_poi_detail": education_poi_detail,
        "education_type_ratio": education_type_ratio,
        "education_concentration": education_concentration,
        "education_density_per_sqkm": education_density,
        "education_support_score": education_support_score
    }
    
    if operation_id:
        global _temp_analysis_results
        if operation_id not in _temp_analysis_results:
            _temp_analysis_results[operation_id] = {}
        _temp_analysis_results[operation_id]["education"] = analysis_result
    
    return analysis_result

def analyze_medical(min_lon, max_lon, min_lat, max_lat, operation_id=None) -> dict:
    """医疗设施POI分析（新增）"""
    logger.info("开始医疗设施POI分析")
    medical_poi_detail = {}
    total_medical_poi = 0
    
    for poi_name, poi_code in MEDICAL_POI_TYPES.items():
        count = get_poi_count(min_lon, max_lon, min_lat, max_lat, poi_code)
        medical_poi_detail[poi_name] = count
        total_medical_poi += count
    
    medical_density = calculate_density(total_medical_poi, min_lon, max_lon, min_lat, max_lat)
    medical_type_ratio = calculate_type_ratio(medical_poi_detail)
    medical_concentration = calculate_concentration(medical_poi_detail)
    # 医疗配套评分（密度≥5→10分，线性插值）
    medical_support_score = min(10.0, round(medical_density * 2.0, 1))
    
    if not validate_numeric(medical_support_score, 0, 10, "医疗配套评分"):
        medical_support_score = 0.0
    if not validate_numeric(medical_density, 0, None, "医疗POI密度"):
        medical_density = 0.0
    
    analysis_result = {
        "total_medical_poi_count": total_medical_poi,
        "medical_poi_detail": medical_poi_detail,
        "medical_type_ratio": medical_type_ratio,
        "medical_concentration": medical_concentration,
        "medical_density_per_sqkm": medical_density,
        "medical_support_score": medical_support_score
    }
    
    if operation_id:
        global _temp_analysis_results
        if operation_id not in _temp_analysis_results:
            _temp_analysis_results[operation_id] = {}
        _temp_analysis_results[operation_id]["medical"] = analysis_result
    
    return analysis_result

# ========== 核心扩展5：优化原有分析函数（补充新维度+校验） ==========
def analyze_traffic(min_lon, max_lon, min_lat, max_lat, operation_id=None):
    """交通POI分析（优化：新增占比+集中度+数值校验）"""
    logger.info("开始交通POI分析")
    traffic_poi_detail = {}
    total_traffic_poi = 0
    
    for poi_name, poi_code in TRAFFIC_POI_TYPES.items():
        count = get_poi_count(min_lon, max_lon, min_lat, max_lat, poi_code)
        traffic_poi_detail[poi_name] = count
        total_traffic_poi += count
    
    traffic_density = calculate_density(total_traffic_poi, min_lon, max_lon, min_lat, max_lat)
    traffic_convenience_score = min(10.0, round(traffic_density * 0.2, 1))
    
    # 新增：占比+集中度
    traffic_type_ratio = calculate_type_ratio(traffic_poi_detail)
    traffic_concentration = calculate_concentration(traffic_poi_detail)
    
    # 新增：数值校验
    if not validate_numeric(traffic_convenience_score, 0, 10, "交通便利度评分"):
        traffic_convenience_score = 0.0
    if not validate_numeric(traffic_density, 0, None, "交通POI密度"):
        traffic_density = 0.0
    
    traffic_analysis = {
        "total_traffic_poi_count": total_traffic_poi,
        "traffic_poi_detail": traffic_poi_detail,
        "traffic_type_ratio": traffic_type_ratio,  # 新增
        "traffic_concentration": traffic_concentration,  # 新增
        "traffic_density_per_sqkm": traffic_density,
        "traffic_convenience_score": traffic_convenience_score
    }
    
    if operation_id:
        global _temp_analysis_results
        if operation_id not in _temp_analysis_results:
            _temp_analysis_results[operation_id] = {}
        _temp_analysis_results[operation_id]["traffic"] = traffic_analysis
    
    return traffic_analysis

def analyze_culture(min_lon, max_lon, min_lat, max_lat, operation_id=None):
    """文化POI分析（优化：新增占比+集中度+交叉洞察）"""
    logger.info("开始文化POI分析")
    culture_poi_detail = {}
    total_culture_poi = 0
    
    for poi_name, poi_code in CULTURE_POI_TYPES.items():
        count = get_poi_count(min_lon, max_lon, min_lat, max_lat, poi_code)
        culture_poi_detail[poi_name] = count
        total_culture_poi += count
    
    culture_density = calculate_density(total_culture_poi, min_lon, max_lon, min_lat, max_lat)
    culture_feature_score = min(10.0, round(culture_density * 1.0, 1))
    
    # 新增：占比+集中度
    culture_type_ratio = calculate_type_ratio(culture_poi_detail)
    culture_concentration = calculate_concentration(culture_poi_detail)
    
    # 数值校验（保留并优化）
    if not validate_numeric(culture_feature_score, 0, 10, "文化特色指数"):
        culture_feature_score = 0.0
    if not validate_numeric(culture_density, 0, None, "文化POI密度"):
        culture_density = 0.0
    
    culture_analysis = {
        "total_culture_poi_count": total_culture_poi,
        "culture_poi_detail": culture_poi_detail,
        "culture_type_ratio": culture_type_ratio,  # 新增
        "culture_concentration": culture_concentration,  # 新增
        "culture_density_per_sqkm": culture_density,
        "culture_feature_score": culture_feature_score
    }
    
    # ========== 核心优化：合并所有类别结果写入数据库 ==========
    if operation_id:
        # 获取所有暂存的分析结果（交通+生活+商业+教育+医疗）
        traffic_analysis = _temp_analysis_results.get(operation_id, {}).get("traffic", {})
        life_analysis = _temp_analysis_results.get(operation_id, {}).get("life", {})
        commercial_analysis = _temp_analysis_results.get(operation_id, {}).get("commercial", {})
        education_analysis = _temp_analysis_results.get(operation_id, {}).get("education", {})
        medical_analysis = _temp_analysis_results.get(operation_id, {}).get("medical", {})
        
        # 新增：交叉分析洞察
        insights = generate_cross_insights(
            traffic_analysis, culture_analysis, life_analysis,
            commercial_analysis, education_analysis, medical_analysis
        )
        
        # 构造插入参数（扩展新增类别的字段）
        current_time = db.get_current_time()
        insert_params = (
            operation_id,
            # 交通类（原有）
            traffic_analysis.get("total_traffic_poi_count", 0),
            traffic_analysis.get("traffic_density_per_sqkm", 0.0),
            traffic_analysis.get("traffic_convenience_score", 0.0),
            json.dumps(traffic_analysis.get("traffic_poi_detail", {})),
            json.dumps(traffic_analysis.get("traffic_type_ratio", {})),  # 新增
            # 文化类（原有）
            culture_analysis.get("total_culture_poi_count", 0),
            culture_analysis.get("culture_density_per_sqkm", 0.0),
            culture_analysis.get("culture_feature_score", 0.0),
            json.dumps(culture_analysis.get("culture_poi_detail", {})),
            json.dumps(culture_analysis.get("culture_type_ratio", {})),  # 新增
            # 新增类别
            life_analysis.get("total_life_poi_count", 0),
            life_analysis.get("life_density_per_sqkm", 0.0),
            life_analysis.get("life_convenience_score", 0.0),
            json.dumps(life_analysis.get("life_poi_detail", {})),
            commercial_analysis.get("total_commercial_poi_count", 0),
            commercial_analysis.get("commercial_density_per_sqkm", 0.0),
            commercial_analysis.get("commercial_activity_score", 0.0),
            json.dumps(commercial_analysis.get("commercial_poi_detail", {})),
            education_analysis.get("total_education_poi_count", 0),
            education_analysis.get("education_density_per_sqkm", 0.0),
            education_analysis.get("education_support_score", 0.0),
            json.dumps(education_analysis.get("education_poi_detail", {})),
            medical_analysis.get("total_medical_poi_count", 0),
            medical_analysis.get("medical_density_per_sqkm", 0.0),
            medical_analysis.get("medical_support_score", 0.0),
            json.dumps(medical_analysis.get("medical_poi_detail", {})),
            # 交叉洞察
            json.dumps(insights),
            current_time,
            current_time
        )
        
        # 执行插入（需同步更新数据库表结构，新增对应字段）
        insert_sql = """
        INSERT INTO analysis_results 
        (operation_id,
         -- 交通类
         total_traffic_poi, traffic_density, traffic_convenience_score, traffic_poi_detail, traffic_type_ratio,
         -- 文化类
         total_culture_poi, culture_density, culture_feature_score, culture_poi_detail, culture_type_ratio,
         -- 生活类
         total_life_poi, life_density, life_convenience_score, life_poi_detail,
         -- 商业类
         total_commercial_poi, commercial_density, commercial_activity_score, commercial_poi_detail,
         -- 教育类
         total_education_poi, education_density, education_support_score, education_poi_detail,
         -- 医疗类
         total_medical_poi, medical_density, medical_support_score, medical_poi_detail,
         -- 其他
         insights, create_time, update_time)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        insert_result = db.execute(insert_sql, insert_params, commit=True)
        if insert_result is None:
            logger.warning("分析结果写入数据库失败（文件生成不受影响）")
        else:
            logger.info("分析结果写入数据库成功（含6大类POI+交叉洞察）")
        
        # 清理暂存数据
        if operation_id in _temp_analysis_results:
            del _temp_analysis_results[operation_id]
    
    return culture_analysis

# ========== 核心扩展6：生成交叉分析洞察（提升分析价值） ==========
def generate_cross_insights(traffic, culture, life, commercial, education, medical) -> list:
    """基于多类POI数据生成深度交叉洞察"""
    insights = []
    place_name = "目标区域"  # 可从外部传入，此处默认
    
    # 1. 综合配套评分
    total_score = (
        traffic.get("traffic_convenience_score", 0.0) +
        culture.get("culture_feature_score", 0.0) +
        life.get("life_convenience_score", 0.0) +
        commercial.get("commercial_activity_score", 0.0) +
        education.get("education_support_score", 0.0) +
        medical.get("medical_support_score", 0.0)
    )
    avg_score = round(total_score / 6, 1)
    insights.append(f"{place_name}综合配套评分为{avg_score}分（满分10分），{'配套完善' if avg_score >= 7 else '配套一般' if avg_score >= 4 else '配套薄弱'}")
    
    # 2. 交通-商业关联性
    traffic_density = traffic.get("traffic_density_per_sqkm", 0.0)
    commercial_density = commercial.get("commercial_density_per_sqkm", 0.0)
    traffic_commercial_corr = correlate_poi_densities(traffic_density, commercial_density)
    if traffic_commercial_corr >= 0.7:
        insights.append(f"交通与商业配套关联性强（相关系数{traffic_commercial_corr}），出行便利度高的区域商业活跃度也高")
    
    # 3. 生活服务主导类型
    life_ratio = life.get("life_type_ratio", {})
    if life_ratio:
        top_life_type = max(life_ratio.items(), key=lambda x: x[1])[0]
        insights.append(f"生活服务以{top_life_type}为主（占比{life_ratio[top_life_type]}%），日常购物/办事便利性{'高' if life.get('life_convenience_score', 0) >= 7 else '中等'}")
    
    # 4. 教育-医疗配套均衡性
    education_score = education.get("education_support_score", 0.0)
    medical_score = medical.get("medical_support_score", 0.0)
    score_diff = abs(education_score - medical_score)
    if score_diff <= 2.0:
        insights.append(f"教育与医疗配套均衡（评分差{score_diff}分），适合居住")
    else:
        insights.append(f"教育与医疗配套不均衡（评分差{score_diff}分），{'教育资源更丰富' if education_score > medical_score else '医疗资源更丰富'}")
    
    # 5. 商业集中度洞察
    commercial_concentration = commercial.get("commercial_concentration", 0.0)
    if commercial_concentration > 5.0:
        top_commercial_type = max(commercial.get("commercial_type_ratio", {}).items(), key=lambda x: x[1])[0]
        insights.append(f"商业设施集中度高（标准差{commercial_concentration}），{top_commercial_type}占主导地位，商业形态单一")
    
    return insights

# ========== 全局暂存分析结果（扩展支持多类别） ==========
_temp_analysis_results = {}

# ========== 核心扩展7：新增自定义POI分析接口（灵活扩展） ==========
def analyze_custom_poi(min_lon, max_lon, min_lat, max_lat, custom_poi_types: dict, operation_id=None) -> dict:
    """
    自定义POI分析（支持用户传入任意POI类型字典，扩展灵活性）
    :param custom_poi_types: 自定义POI类型字典，格式{"名称": "类型码"}
    """
    logger.info("开始自定义POI分析")
    if not custom_poi_types:
        logger.warning("自定义POI类型字典为空，返回空结果")
        return {}
    
    custom_poi_detail = {}
    total_custom_poi = 0
    for poi_name, poi_code in custom_poi_types.items():
        count = get_poi_count(min_lon, max_lon, min_lat, max_lat, poi_code)
        custom_poi_detail[poi_name] = count
        total_custom_poi += count
    
    custom_density = calculate_density(total_custom_poi, min_lon, max_lon, min_lat, max_lat)
    custom_type_ratio = calculate_type_ratio(custom_poi_detail)
    
    analysis_result = {
        "total_custom_poi_count": total_custom_poi,
        "custom_poi_detail": custom_poi_detail,
        "custom_type_ratio": custom_type_ratio,
        "custom_density_per_sqkm": custom_density
    }
    
    if operation_id:
        global _temp_analysis_results
        if operation_id not in _temp_analysis_results:
            _temp_analysis_results[operation_id] = {}
        _temp_analysis_results[operation_id]["custom"] = analysis_result
    
    logger.info(f"自定义POI分析完成：共{total_custom_poi}个POI，密度{custom_density}个/平方公里")
    return analysis_result

# ========== 测试用例（扩展覆盖所有新功能） ==========
if __name__ == "__main__":
    # 测试区域：北京中关村
    min_lon, max_lon = 116.30, 116.33
    min_lat, max_lat = 39.97, 40.00
    op_id = "20260212_163000_8f9e7d"
    
    # 执行全量分析（原有+新增）
    analyze_traffic(min_lon, max_lon, min_lat, max_lat, operation_id=op_id)
    analyze_life(min_lon, max_lon, min_lat, max_lat, operation_id=op_id)
    analyze_commercial(min_lon, max_lon, min_lat, max_lat, operation_id=op_id)
    analyze_education(min_lon, max_lon, min_lat, max_lat, operation_id=op_id)
    analyze_medical(min_lon, max_lon, min_lat, max_lat, operation_id=op_id)
    analyze_culture(min_lon, max_lon, min_lat, max_lat, operation_id=op_id)
    
    # 测试自定义POI分析（示例：体育设施）
    custom_poi = {"篮球场": "110100", "足球场": "110101", "健身房": "110500"}
    analyze_custom_poi(min_lon, max_lon, min_lat, max_lat, custom_poi, operation_id=op_id)
    
    logger.info("全量分析测试完成！")
=======
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
>>>>>>> f8d32f88976298bf651187a413419c65a4f0185b
