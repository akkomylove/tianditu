# image_merger.py 改造版（核心修改处标注）
import os
import glob
from PIL import Image
import logging
# ========== 新增导入 ==========
from db_utils import db
from utils import get_file_size
from data_validator import validate_file_path, validate_zoom_level, validate_numeric  # 补全校验函数
from db_utils import logger  # 补全 logger

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("image_merger")

def merge_tiles(tiles_dir, zoom_level, output_path, operation_id=None):
    """
    拼接瓦片为完整地图
    :param tiles_dir: 瓦片文件夹
    :param zoom_level: 缩放等级
    :param output_path: 输出路径
    :param operation_id: 操作唯一标识（新增）
    :return: 拼接成功返回True，失败返回False
    """
    try:
        if not validate_zoom_level(zoom_level):
            logger.error("缩放等级校验失败")
            return False
        if not validate_file_path(output_path, must_exist=False):
            logger.error("输出路径校验失败")
            return False
        # 校验参数
        if not os.path.exists(tiles_dir):
            logger.error(f"瓦片文件夹不存在：{tiles_dir}")
            return False
        
        # 获取所有瓦片文件
        tile_files = glob.glob(os.path.join(tiles_dir, f"{zoom_level}_*.png"))
        if not tile_files:
            logger.error(f"未找到瓦片文件：{tiles_dir}")
            return False
        
        # 解析瓦片坐标（保持原有逻辑）
        tile_coords = []
        for tile_file in tile_files:
            filename = os.path.basename(tile_file)
            parts = filename.replace(".png", "").split("_")
            if len(parts) != 3:
                continue
            z, x, y = parts
            tile_coords.append((int(x), int(y), tile_file))
        
        if not tile_coords:
            logger.error("未解析到有效瓦片坐标")
            return False
        
        # 排序瓦片（保持原有逻辑）
        tile_coords.sort(key=lambda x: (x[1], x[0]))  # 按y升序，x升序
        min_x = min([x[0] for x in tile_coords])
        max_x = max([x[0] for x in tile_coords])
        min_y = min([x[1] for x in tile_coords])
        max_y = max([x[1] for x in tile_coords])
        
        # 计算拼接后尺寸（保持原有逻辑）
        tile_size = 256
        width = (max_x - min_x + 1) * tile_size
        height = (max_y - min_y + 1) * tile_size
        merged_image = Image.new("RGB", (width, height))
        
        # 拼接瓦片（保持原有逻辑）
        for x, y, tile_file in tile_coords:
            try:
                tile = Image.open(tile_file).convert("RGB")
                x_offset = (x - min_x) * tile_size
                y_offset = (y - min_y) * tile_size
                merged_image.paste(tile, (x_offset, y_offset))
            except Exception as e:
                logger.warning(f"跳过损坏的瓦片：{tile_file}，错误：{str(e)}")
                continue
        
        # 保存拼接图（保持原有逻辑）
        merged_image.save(output_path, quality=95)
        logger.info(f"拼接图保存成功：{output_path}")
        
        file_size = get_file_size(output_path)
        if not validate_numeric(file_size, min_value=1, field_name="拼接图文件大小"):
            logger.warning("⚠️ 拼接图文件大小异常（可能为空文件）")
        
        # ========== 核心改造：写入拼接地图表 ==========
        if operation_id:
            logger.info(f"写入拼接地图信息到数据库（operation_id：{operation_id}）")
            current_time = db.get_current_time()
            file_size = get_file_size(output_path)
            # 构造插入参数
            insert_params = (
                operation_id,
                os.path.abspath(output_path),
                width,
                height,
                file_size,
                current_time,
                current_time
            )
            # 执行插入
            insert_sql = """
            INSERT INTO merged_maps 
            (operation_id, merged_path, width, height, file_size, create_time, update_time)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            insert_result = db.execute(insert_sql, insert_params, commit=True)
            if insert_result is None:
                logger.warning("拼接地图信息写入数据库失败（文件已保存）")
            else:
                logger.info("拼接地图信息写入数据库成功")
        
        return True
    except Exception as e:
        logger.error(f"瓦片拼接失败：{str(e)}", exc_info=True)
        return False

# 测试用例（保持原有，新增operation_id参数）
if __name__ == "__main__":
    merge_tiles(
        tiles_dir="output/test/tiles",
        zoom_level=15,
        output_path="output/test/merged_map.jpg",
        operation_id="20260212_163000_8f9e7d"
    )