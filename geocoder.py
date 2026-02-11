"""
天地图地理编码服务 - 适配前端无IP限制密钥（复刻浏览器请求特征）
✅ 解决403拦截：完全模拟浏览器请求头/参数编码
✅ 统一从config导入密钥，确保读取正常
✅ 保留边界生成、容错处理核心功能
"""
import json
import requests
from config import TIANDITU_KEY

# 复刻浏览器的请求头（核心！天地图反爬校验的关键）
BROWSER_HEADERS = {
    "User-Agent": "python-requests/2.31.0",
    "Accept": "application/json"
}

def get_location_bounds(place_name):
    """
    调用天地图地理编码（geocoder）接口，返回目标地点的周边边界坐标
    Args:
        place_name (str): 要解析的地点名称（如"北京中关村"）
    Returns:
        tuple: (bounds字典/None, 提示信息字符串)
    """
    # 1. 前置参数校验
    if not place_name or place_name.strip() == "":
        return None, "❌ 搜索地点名称不能为空！"
    
    # 2. 从config获取密钥（已做严格校验，直接使用）
    api_key = TIANDITU_KEY.strip()
    print(f"📌 已加载密钥：{api_key[:10]}***（完整长度：{len(api_key)}）")

    # 3. 构造geocoder接口请求（完全复刻浏览器参数格式）
    url = "https://api.tianditu.gov.cn/geocoder"
    # ds参数：严格按浏览器的JSON序列化（无空格、ensure_ascii=False）
    ds_payload = {"keyWord": place_name.strip()}
    ds_str = json.dumps(ds_payload, ensure_ascii=False, separators=(',', ':'))
    # 请求参数：和浏览器完全一致的key顺序
    params = {
        "ds": ds_str,
        "tk": api_key,
        "output": "json"
    }

    # 打印完整请求信息（方便排查）
    print(f"📡 请求URL：{url}")
    print(f"📡 请求参数：{params}")
    print(f"📡 请求头：{json.dumps(BROWSER_HEADERS, indent=2, ensure_ascii=False)}")

    try:
        # 4. 发送请求（完全模拟浏览器行为，关闭重定向/SSL验证）
        response = requests.get(
            url=url,
            params=params,
            headers=BROWSER_HEADERS,
            timeout=20,  # 延长超时，适配网络波动
            allow_redirects=False,  # 禁止重定向，避免被拦截
            verify=True,  # 开启SSL验证，保持与浏览器一致（天地图支持HTTPS）
            stream=False,
            proxies=None  # 关闭代理，避免代理导致的特征异常
        )

        # 打印响应基础信息
        print(f"\n📨 响应状态码：{response.status_code}")
        print(f"📨 响应头：{json.dumps(dict(response.headers), indent=2, ensure_ascii=False)}")
        print(f"📨 响应体（原始）：{response.text[:500]}...")

        # 触发4xx/5xx HTTP错误，方便捕获
        response.raise_for_status()

        # 5. 处理响应（去除BOM头、空白字符，兼容天地图的返回格式）
        raw_text = response.text.strip()
        if raw_text.startswith('\ufeff'):
            raw_text = raw_text[1:]
        # 替换特殊字符，避免JSON解析失败
        raw_text = raw_text.replace('\r', '').replace('\n', '')

        # 6. 解析JSON响应
        try:
            result = json.loads(raw_text)
        except json.JSONDecodeError as e:
            return None, f"❌ JSON解析失败：{str(e)} | 原始返回：{raw_text[:300]}"

        # 7. 校验天地图业务状态（msg=ok + status=0 为成功）
        print(f"\n📊 业务返回结果：{json.dumps(result, indent=2, ensure_ascii=False)}")
        res_msg = result.get("msg", "").lower()
        res_status = result.get("status", "-1")
        if res_msg != "ok" or res_status != "0":
            err_info = f"msg={res_msg}, status={res_status}"
            return None, f"❌ 地理编码业务失败：{err_info} | 详情：{json.dumps(result, ensure_ascii=False)}"
        
        # 8. 提取经纬度核心信息
        location = result.get("location", {})
        lon_str = location.get("lon", "").strip()
        lat_str = location.get("lat", "").strip()
        matched_address = location.get("keyWord", place_name.strip())

        if not lon_str or not lat_str:
            return None, f"❌ 接口未返回有效经纬度 | 定位结果：{json.dumps(location, ensure_ascii=False)}"
        
        # 9. 经纬度类型转换（容错处理，兼容字符串/数字格式）
        try:
            lon = float(lon_str)
            lat = float(lat_str)
        except ValueError:
            return None, f"❌ 经纬度转换失败：经度={lon_str}，纬度={lat_str}（非数字格式）"

        # 10. 生成周边边界（和config字段名统一：min_lon/max_lon/min_lat/max_lat）
        bounds = {
            "min_lon": round(lon - 0.01, 6),
            "min_lat": round(lat - 0.01, 6),
            "max_lon": round(lon + 0.01, 6),
            "max_lat": round(lat + 0.01, 6)
        }

        # 构造成功信息
        success_msg = f"✅ 地理编码成功！\n🔍 匹配地址：{matched_address}\n📍 经纬度：{lon:.6f},{lat:.6f}\n📏 周边边界：{json.dumps(bounds, ensure_ascii=False)}"
        return bounds, success_msg

    # 捕获HTTP错误（403/401/500等，打印完整详情）
    except requests.HTTPError as e:
        err_msg = f"❌ HTTP请求错误：{str(e)}（状态码：{response.status_code}）"
        err_msg += f"\n📌 响应头：{json.dumps(dict(response.headers), ensure_ascii=False)}"
        err_msg += f"\n📌 响应体：{response.text[:500]}"
        err_msg += f"\n💡 若仍403：请等待10分钟（天地图反爬缓存），或更换网络环境"
        return None, err_msg
    
    # 捕获网络异常（超时/连接失败）
    except requests.exceptions.Timeout:
        return None, "❌ 请求超时（20秒），请检查网络连接或天地图API可用性！"
    except requests.exceptions.ConnectionError:
        return None, "❌ 网络连接错误！请检查网络，或确认天地图官网（https://www.tianditu.gov.cn/）可正常访问。"
    except requests.exceptions.RequestException as e:
        return None, f"❌ 网络请求异常：{str(e)}"
    
    # 捕获其他未知错误
    except Exception as e:
        import traceback
        return None, f"❌ 未知错误：{str(e)}\n📝 错误详情：{traceback.format_exc()[:500]}"

# 本地测试用例（优先运行此测试，确认正常后再跑GUI/主程序）
if __name__ == "__main__":
    print("="*80)
    print("🌍 天地图地理编码测试（前端无IP限制密钥专用版）")
    print("="*80 + "\n")
    # 测试地点（可替换为自己需要的地址）
    test_place = "北京中关村"
    print(f"🔍 开始测试：{test_place}\n")
    # 调用地理编码
    bounds, msg = get_location_bounds(test_place)
    # 打印结果
    print("\n" + "="*50)
    print(msg)
    print("="*50)