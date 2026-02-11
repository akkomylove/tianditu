import os
from PIL import Image
from config import TILE_DIR, MERGED_IMAGE, ZOOM_LEVEL
import math

def merge_tiles(metadata_df):
    """按坐标拼接瓦片成大图"""
    if metadata_df.empty:
        print("❌ 无瓦片数据，跳过拼接")
        return False
    
    # 计算拼接尺寸（256px/瓦片）
    x_vals = metadata_df['x'].unique()
    y_vals = metadata_df['y'].unique()
    width = len(x_vals) * 256
    height = len(y_vals) * 256
    
    print(f"🖼️  开始拼接 ({len(x_vals)}x{len(y_vals)} 瓦片)...")
    merged = Image.new('RGB', (width, height))
    
    x_sorted = sorted(x_vals)
    y_sorted = sorted(y_vals)
    
    for _, row in metadata_df.iterrows():
        tile_path = os.path.join(TILE_DIR, f"tile_{int(row['x'])}_{int(row['y'])}.png")
        if os.path.exists(tile_path):
            try:
                tile = Image.open(tile_path)
                x_idx = x_sorted.index(row['x'])
                y_idx = y_sorted.index(row['y'])
                merged.paste(tile, (x_idx * 256, y_idx * 256))
            except Exception as e:
                print(f"⚠️ 拼接错误 {tile_path}: {e}")
    
    os.makedirs(os.path.dirname(MERGED_IMAGE), exist_ok=True)
    merged.save(MERGED_IMAGE, quality=95)
    print(f"✅ 拼接完成！保存至: {MERGED_IMAGE}")
    return True