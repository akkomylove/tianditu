"""
数据校验工具类 - 阶段4新增
✅ 校验文件路径（存在性/格式）
✅ 校验经纬度（范围/合理性）
✅ 校验数值（非负/范围）
✅ 校验operation_id格式
"""
import os
import re
import logging

# 配置日志
logger = logging.getLogger("data_validator")
# 定义各系统的非法字符（核心：Windows排除盘符冒号）
ILLEGAL_CHARS_WIN = r'*?"<>|'
# 判断当前系统
IS_WINDOWS = os.name == 'nt'
# 正则：operation_id格式（YYYYMMDD_HHMMSS_6位随机串）
OPERATION_ID_PATTERN = re.compile(r"^\d{8}_\d{6}_[a-z0-9]{6}$")

# 中国境内经纬度范围
CHINA_LON_RANGE = (73.0, 135.0)
CHINA_LAT_RANGE = (4.0, 53.0)

# 缩放等级范围
ZOOM_LEVEL_RANGE = (1, 18)

def validate_operation_id(operation_id):
    """校验operation_id格式"""
    if not isinstance(operation_id, str):
        logger.error(f"❌ operation_id不是字符串类型：{type(operation_id)}")
        return False
    if not OPERATION_ID_PATTERN.match(operation_id):
        logger.error(f"❌ operation_id格式错误：{operation_id}（需匹配YYYYMMDD_HHMMSS_6位随机串）")
        return False
    return True

def validate_coords(min_lon, max_lon, min_lat, max_lat):
    """校验经纬度（中国境内+最大值>最小值）"""
    try:
        min_lon = float(min_lon)
        max_lon = float(max_lon)
        min_lat = float(min_lat)
        max_lat = float(max_lat)
        
        # 范围校验
        if not (CHINA_LON_RANGE[0] <= min_lon <= max_lon <= CHINA_LON_RANGE[1]):
            logger.error(f"❌ 经度范围错误：{min_lon}~{max_lon}（需在73.0~135.0之间，且min≤max）")
            return False
        if not (CHINA_LAT_RANGE[0] <= min_lat <= max_lat <= CHINA_LAT_RANGE[1]):
            logger.error(f"❌ 纬度范围错误：{min_lat}~{max_lat}（需在4.0~53.0之间，且min≤max）")
            return False
        return True
    except (ValueError, TypeError):
        logger.error(f"❌ 经纬度不是有效数值：min_lon={min_lon}, max_lon={max_lon}, min_lat={min_lat}, max_lat={max_lat}")
        return False

def validate_zoom_level(zoom_level):
    """校验缩放等级"""
    try:
        zoom_level = int(zoom_level)
        if not (ZOOM_LEVEL_RANGE[0] <= zoom_level <= ZOOM_LEVEL_RANGE[1]):
            logger.error(f"❌ 缩放等级错误：{zoom_level}（需在1~18之间）")
            return False
        return True
    except (ValueError, TypeError):
        logger.error(f"❌ 缩放等级不是有效整数：{zoom_level}")
        return False

def validate_file_path(file_path, must_exist=False):
    """
    校验文件路径合法性（跨平台适配：Windows允许盘符冒号，Linux/Mac禁止冒号）
    :param file_path: 待校验路径
    :param must_exist: 是否要求路径已存在
    :return: 合法返回True，非法返回False
    """
    try:
        # 1. 空路径校验
        if not file_path or not str(file_path).strip():
            logger.error("❌ 文件路径不能为空！")
            return False
        file_path = str(file_path).strip()

        # 2. 路径存在性校验（如果要求必须存在）
        if must_exist and not os.path.exists(file_path):
            logger.error(f"❌ 文件路径不存在：{file_path}")
            return False

        # 3. 跨平台非法字符校验（核心修复：适配Windows盘符冒号）
        illegal_chars = ILLEGAL_CHARS_WIN if IS_WINDOWS else ILLEGAL_CHARS_UNIX
        # 提取路径中的纯字符部分（排除Windows盘符：如C:\ -> 从第3位开始校验）
        check_path = file_path[2:] if IS_WINDOWS and len(file_path)>=3 and file_path[1] == ':' else file_path
        # 检查是否包含非法字符
        for char in illegal_chars:
            if char in check_path:
                logger.error(f"❌ 文件路径包含非法字符：{char}（路径：{file_path}）")
                return False

        # 4. 路径长度校验（可选，防止系统最大路径限制）
        if len(file_path) > 260:
            logger.warning("⚠️ 文件路径过长，可能超出系统最大路径限制（建议缩短）")

        return True
    except Exception as e:
        logger.error(f"❌ 文件路径校验异常：{str(e)}（路径：{file_path}）")
        return False

def validate_numeric(value, min_value=0, max_value=None, field_name="数值"):
    """校验数值（非负/范围）"""
    try:
        value = float(value)
        if value < min_value:
            logger.error(f"❌ {field_name}小于最小值{min_value}：{value}")
            return False
        if max_value is not None and value > max_value:
            logger.error(f"❌ {field_name}大于最大值{max_value}：{value}")
            return False
        return True
    except (ValueError, TypeError):
        logger.error(f"❌ {field_name}不是有效数值：{value}")
        return False

# 测试用例
if __name__ == "__main__":
    # 测试operation_id校验
    print("operation_id校验（正确）：", validate_operation_id("20260212_173000_8f9e7d"))
    print("operation_id校验（错误）：", validate_operation_id("20260212_17300_8f9e7d"))
    
    # 测试经纬度校验
    print("经纬度校验（正确）：", validate_coords(116.30, 116.33, 39.97, 40.00))
    print("经纬度校验（错误）：", validate_coords(140.0, 150.0, 39.97, 40.00))
    
    # 测试文件路径校验
    print("文件路径校验（正确）：", validate_file_path(os.path.abspath(__file__)))
    print("文件路径校验（错误）：", validate_file_path("C:/test<>.txt"))
    
    # 测试数值校验
    print("数值校验（正确）：", validate_numeric(8.5, 0, 10, "交通便利度"))
    print("数值校验（错误）：", validate_numeric(-1, 0, 10, "交通便利度"))