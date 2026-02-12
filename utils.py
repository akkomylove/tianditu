"""
通用工具函数 - 供各模块复用
✅ 生成唯一operation_id
✅ 创建唯一输出文件夹
✅ 路径/数据校验工具
"""
import os
import random
import string
from datetime import datetime
from config import OUTPUT_DIR

def generate_operation_id():
    """
    生成唯一operation_id（格式：YYYYMMDD_HHMMSS_6位随机串）
    :return: 如 "20260212_163000_8f9e7d"
    """
    # 时间戳部分（YYYYMMDD_HHMMSS）
    time_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    # 6位随机串（小写字母+数字）
    random_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return f"{time_str}_{random_str}"

def create_unique_output_dir(operation_id):
    """
    创建本次操作的唯一输出文件夹（避免覆盖）
    :param operation_id: 操作唯一标识
    :return: 文件夹绝对路径（如 "output/20260212_163000_8f9e7d/"）
    """
    # 拼接唯一文件夹路径
    unique_dir = os.path.join(OUTPUT_DIR, operation_id)
    # 递归创建文件夹（不存在则创建，存在则忽略）
    os.makedirs(unique_dir, exist_ok=True)
    # 创建子文件夹（瓦片/报告等）
    os.makedirs(os.path.join(unique_dir, "tiles"), exist_ok=True)
    return os.path.abspath(unique_dir)  # 返回绝对路径

def validate_coords(min_lon, max_lon, min_lat, max_lat):
    """
    校验经纬度是否在中国境内（基础校验）
    :return: 校验通过返回True，否则False
    """
    try:
        min_lon = float(min_lon)
        max_lon = float(max_lon)
        min_lat = float(min_lat)
        max_lat = float(max_lat)
        # 中国境内经纬度范围
        if 73.0 <= min_lon <= max_lon <= 135.0 and 4.0 <= min_lat <= max_lat <= 53.0:
            return True
        return False
    except (ValueError, TypeError):
        return False

def get_file_size(file_path):
    """
    获取文件大小（字节）
    :return: 文件大小（字节），文件不存在返回0
    """
    if os.path.exists(file_path):
        return os.path.getsize(file_path)
    return 0