import os
import requests
from math import floor
import time
import pandas as pd
from config import (
    TIANDITU_KEY, DEFAULT_ZOOM_LEVEL, BOUNDS, TILE_DIR,
    TIANDITU_TILE_TYPES, DEFAULT_TILE_TYPE
)
import math


def lonlat_to_tile(lon, lat, zoom):
    """经纬度转瓦片坐标（天地图使用Google XYZ scheme）"""
    n = 2 ** zoom
    x = int((lon + 180) / 360 * n)
    y = int((1 - (math.log(math.tan(math.radians(lat)) + 1 / math.cos(math.radians(lat)))) / math.pi) / 2 * n)
    return x, y

def fetch_tiles(bounds, zoom_level=None, tile_url_template=None):
    """下载瓦片并记录元数据"""
    from config import DEFAULT_ZOOM_LEVEL, TIANDITU_TILE_TYPES, DEFAULT_TILE_TYPE
    zoom_level = zoom_level or DEFAULT_ZOOM_LEVEL
    tile_url_template = tile_url_template or TIANDITU_TILE_TYPES[DEFAULT_TILE_TYPE]["url_template"]
    
    
    os.makedirs(TILE_DIR, exist_ok=True)
    if bounds is None:
        from config import BOUNDS
        bounds = BOUNDS
    
    # 计算瓦片范围
    x_min, y_max = lonlat_to_tile(bounds["min_lon"], bounds["min_lat"], zoom_level)
    x_max, y_min = lonlat_to_tile(bounds["max_lon"], bounds["max_lat"], zoom_level)
    
    metadata = []
    tile_count = 0
    
    print(f"📍 正在下载瓦片（范围: x[{x_min}-{x_max}], y[{y_min}-{y_max}]）...")
    for x in range(x_min, x_max + 1):
        for y in range(y_min, y_max + 1):
            url = tile_url_template.format(x=x, y=y, z=zoom_level)
            path = os.path.join(TILE_DIR, f"tile_{x}_{y}.png")
            
            try:
                resp = requests.get(url, timeout=10)
                if resp.status_code == 200:
                    with open(path, 'wb') as f:
                        f.write(resp.content)
                    # 记录元数据（用于后续分析）
                    metadata.append({
                        "x": x, "y": y, "zoom": zoom_level,
                        "lon_center": (x + 0.5) * 360 / (2**zoom_level) - 180,
                        "lat_center": math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (y + 0.5) / (2**zoom_level))))),
                        "download_time": time.time(),
                        "file_size_kb": len(resp.content) / 1024
                    })
                    tile_count += 1
                    if tile_count % 20 == 0:
                        print(f"✅ 已下载 {tile_count} 张瓦片...")
                time.sleep(0.1)  # 避免请求过快
            except Exception as e:
                print(f"⚠️ 下载失败 ({x},{y}): {str(e)}")
    
    print(f"✅ 瓦片下载完成！共 {tile_count} 张")
    return pd.DataFrame(metadata) if metadata else pd.DataFrame()