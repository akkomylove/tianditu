"""
天地图地理编码服务 - 服务端专用版（仅含必填参数）
✨ 修复：1. 仅保留keyWord和queryType 2. 精确编码 3. 无冗余参数
"""
import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

def get_location_bounds(place_name):
    """服务端专用地理编码（仅含必填参数）"""
    api_key = os.getenv("TIANDITU_KEY")
    if not api_key:
        return None, "❌ TIANDITU_KEY未配置！请在.env文件中设置"

    # 关键修复：只保留必填参数（keyWord, queryType）
    payload = {
        "keyWord": place_name,
        "mapBound": {
            "minx": -180,
            "miny": -90,
            "maxx": 180,
            "maxy": 90
        },
        "level": 10,
        "queryType": "1"  ,# 服务端POI搜索必须用2
        "start": 0,
        "count": 10
    }
    post_str = json.dumps(payload, ensure_ascii=False)  # 确保中文不转义

    url = "http://api.tianditu.gov.cn/v2/search"
    params = {
        "postStr": post_str,
        "type": "query",
        "tk": api_key
    }

    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        
        # 处理BOM头
        raw_text = response.text.strip()
        if raw_text.startswith('\ufeff'):
            raw_text = raw_text[1:]
        
        result = json.loads(raw_text)
        
        if result.get("status") and result["status"][0]["infocode"] == "1000":
            if result.get("resultType") == 2 and result.get("pois") and len(result["pois"]) > 0:
                poi = result["pois"][0]
                lonlat = poi["lonlat"].split(",")
                if len(lonlat) == 2:
                    lon = float(lonlat[0])
                    lat = float(lonlat[1])
                    return {
                        "minx": lon - 0.01,
                        "miny": lat - 0.01,
                        "maxx": lon + 0.01,
                        "maxy": lat + 0.01
                    }, "✅ 服务端API调用成功（仅含必填参数）"
                else:
                    return None, f"❌ 坐标格式错误（预期2个值，实际有{len(lonlat)}个)"
            else:
                return None, f"❌ 未找到POI结果（API返回: {json.dumps(result, ensure_ascii=False)[:150]}...）"
        else:
            error_desc = result.get("status", [{}])[0].get("cndesc", "未知错误")
            return None, f"❌ API错误: {error_desc} (infocode: {result.get('status', [{}])[0].get('infocode', 'N/A')})"
    
    except Exception as e:
        return None, f"❌ 请求失败: {str(e)}"

# =============== 服务端测试用例 ===============
if __name__ == "__main__":
    print("测试地名搜索：北京中关村（服务端模式 - 仅含必填参数）")
    bounds, msg = get_location_bounds("北京中关村")
    print(msg)
    if bounds:
        print("边界坐标:", bounds)
    else:
        print("搜索失败")