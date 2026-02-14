import requests
import os
import logging
import math  # 补全math导入
from config import TIANDITU_KEY, TIANDITU_TILE_TYPES
from db_utils import db

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("image_fetcher")

# 经纬度转瓦片坐标（保持原有逻辑，和你参考代码的tileRow/tileCol入参匹配）
def lonlat2tile(lon, lat, zoom):
    try:
        lat_rad = math.radians(lat)
        n = 2.0 ** zoom
        xtile = int((lon + 180.0) / 360.0 * n)
        ytile = int((1.0 - math.log(math.tan(lat_rad) + (1 / math.cos(lat_rad))) / math.pi) / 2.0 * n)
        return xtile, ytile
    except Exception as e:
        logger.error(f"经纬度转瓦片坐标失败：{str(e)}")
        return None, None

def download_tiles(min_lon, max_lon, min_lat, max_lat, zoom_level, tile_type, output_dir, operation_id=None):
    """
    下载瓦片（完全对齐参考代码的URL规则，保留批量/数据库逻辑，无header）
    :return: 下载成功返回True，失败返回False
    """
    try:
        # 用你参考代码的默认KEY（也可从config取，保持一致）
        tk = TIANDITU_KEY if TIANDITU_KEY else "9447e4e09088ad3920ab9babbbf35ddd"
        if not tk or tk.strip() == "your_actual_key_here":
            logger.error("天地图API Key未配置！")
            return False
        
        # 获取瓦片图层名（参考代码的layer=vec/img，无_w，和URL路径的{layer}_w区分）
        tile_type_dict = TIANDITU_TILE_TYPES.get(tile_type, {})
        # 核心：图层名取参考代码的格式（vec/img），而非带_w的vec_w
        layer = tile_type_dict.get("layer", "vec")  # 优先从config配，无则默认vec
        tile_path_code = f"{layer}_w"  # URL路径用的带_w后缀，和参考代码一致
        
        # 计算瓦片范围（原有逻辑，xtile=TileCol，ytile=TileRow）
        min_x, min_y = lonlat2tile(min_lon, max_lat, zoom_level)  # TileCol最小值
        max_x, max_y = lonlat2tile(max_lon, min_lat, zoom_level)  # TileRow最小值
        if min_x is None or min_y is None or max_x is None or max_y is None:
            logger.error("计算瓦片范围失败")
            return False
        
        logger.info(f"瓦片范围：TileCol[{min_x}~{max_x}], TileRow[{min_y}~{max_y}], zoom={zoom_level}")
        os.makedirs(output_dir, exist_ok=True)
        
        tile_metadata_list = []
        download_success_count = 0
        
        # 遍历批量下载（TileCol=x，TileRow=y，和参考代码入参一一对应）
        for tile_col in range(min_x, max_x + 1):
            for tile_row in range(min_y, max_y + 1):
                # ========== 核心：完全对齐参考代码的URL拼接规则 ==========
                # 1. 参数顺序/大小写/取值和参考代码完全一致
                # 2. Format=image/png 而非tiles（参考代码关键正确点）
                # 3. tk放最前面，layer无_w，URL路径是{layer}_w
                # 4. 无任何header，符合服务器端要求
                tile_url = (
                    f"http://t0.tianditu.gov.cn/{tile_path_code}/wmts?tk={tk}&layer={layer}&style=default"
                    f"&tilematrixset=w&Service=WMTS&Request=GetTile&Version=1.0.0"
                    f"&Format=image/png&TileMatrix={zoom_level}&TileRow={tile_row}&TileCol={tile_col}"
                )
                
                tile_filename = f"{zoom_level}_{tile_col}_{tile_row}.png"
                tile_path = os.path.join(output_dir, tile_filename)
                
                # 跳过已下载的有效瓦片（空白文件自动删除重下）
                if os.path.exists(tile_path):
                    if os.path.getsize(tile_path) > 100:  # 有效图片大小阈值
                        logger.info(f"跳过已下载的瓦片：{tile_filename}")
                        tile_metadata_list.append((
                            operation_id, tile_col, tile_row, zoom_level, os.path.abspath(tile_path),
                            "success", db.get_current_time(), db.get_current_time()
                        ))
                        download_success_count += 1
                        continue
                    else:
                        os.remove(tile_path)  # 删除空白文件，重新下载
                
                # 下载瓦片（和参考代码一致：纯requests.get，无header，超时10s）
                try:
                    response = requests.get(tile_url, timeout=10)
                    response.raise_for_status()  # 抛出HTTP错误，和参考代码一致
                    
                    # 保存瓦片（直接写，和参考代码逻辑一致）
                    with open(tile_path, "wb") as f:
                        f.write(response.content)
                    
                    # 校验是否为有效图片（避免空文件）
                    if os.path.getsize(tile_path) < 100:
                        os.remove(tile_path)
                        logger.warning(f"瓦片为空白已删除：{tile_filename} | URL：{tile_url[:100]}...")
                        tile_metadata_list.append((
                            operation_id, tile_col, tile_row, zoom_level, os.path.abspath(tile_path),
                            "failed", db.get_current_time(), db.get_current_time()
                        ))
                        continue
                    
                    logger.info(f"下载瓦片成功：{tile_filename}")
                    download_success_count += 1
                    tile_metadata_list.append((
                        operation_id, tile_col, tile_row, zoom_level, os.path.abspath(tile_path),
                        "success", db.get_current_time(), db.get_current_time()
                    ))
                except Exception as e:
                    logger.warning(f"下载瓦片失败：{tile_filename} | 错误：{str(e)}")
                    tile_metadata_list.append((
                        operation_id, tile_col, tile_row, zoom_level, os.path.abspath(tile_path),
                        "failed", db.get_current_time(), db.get_current_time()
                    ))
        
        # 批量写入数据库（完全保留你原有逻辑，无修改）
        if operation_id and tile_metadata_list:
            logger.info(f"批量写入瓦片信息到数据库（共{len(tile_metadata_list)}条）")
            insert_sql = """
            INSERT INTO tile_metadata 
            (operation_id, tile_x, tile_y, tile_z, tile_path, download_status, create_time, update_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
            insert_count = db.batch_insert(insert_sql, tile_metadata_list, batch_size=50)
            if insert_count != len(tile_metadata_list):
                logger.warning(f"仅成功写入{insert_count}条瓦片信息（共{len(tile_metadata_list)}条）")
        
        # 下载结果校验（完全保留你原有逻辑）
        if download_success_count == 0:
            logger.error("未成功下载任何瓦片！")
            return False
        logger.info(f"瓦片下载完成：成功{download_success_count}条，总计{len(tile_metadata_list)}条")
        return True
    except Exception as e:
        logger.error(f"瓦片下载流程失败：{str(e)}", exc_info=True)
        return False

# 测试用例（保留，适配新的URL规则）
if __name__ == "__main__":
    download_tiles(
        min_lon=116.30, max_lon=116.33,
        min_lat=39.97, max_lat=40.00,
        zoom_level=12,
        tile_type="矢量图",
        output_dir="output/test_tiles",
        operation_id="test_20260212"
    )
