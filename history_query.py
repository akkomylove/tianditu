"""
历史记录查询工具类 - 阶段5新增
✅ 按条件查询历史操作
✅ 关联查询操作对应的瓦片/拼接图/分析结果/报告
✅ 删除历史记录（含文件+数据库）
"""
import os
import shutil
import logging
from db_utils import db
from data_validator import validate_operation_id

# 配置日志
logger = logging.getLogger("history_query")

def query_history_records(
    operation_id=None, 
    place_name=None, 
    status=None,
    start_time=None,
    end_time=None
):
    """
    按条件查询历史操作记录（支持多条件组合）
    :param operation_id: 操作ID（精确匹配）
    :param place_name: 地址（模糊匹配）
    :param status: 状态（success/failed/running）
    :param start_time: 开始时间（YYYY-MM-DD HH:MM:SS）
    :param end_time: 结束时间（YYYY-MM-DD HH:MM:SS）
    :return: 列表（每条为字典，包含操作主表+关联数据）
    """
    try:
        # 基础查询SQL（关联所有表）
        base_sql = """
        SELECT 
            o.*,
            m.merged_path, m.width, m.height,
            a.total_traffic_poi, a.traffic_convenience_score, a.total_culture_poi, a.culture_feature_score,
            r.report_path, r.generate_status
        FROM tianditu_operations o
        LEFT JOIN merged_maps m ON o.operation_id = m.operation_id
        LEFT JOIN analysis_results a ON o.operation_id = a.operation_id
        LEFT JOIN reports r ON o.operation_id = r.operation_id
        WHERE 1=1
        """
        params = []
        
        # 拼接条件
        if operation_id and validate_operation_id(operation_id):
            base_sql += " AND o.operation_id = ?"
            params.append(operation_id)
        if place_name:
            base_sql += " AND o.place_name LIKE ?"
            params.append(f"%{place_name}%")
        if status in ["success", "failed", "running"]:
            base_sql += " AND o.status = ?"
            params.append(status)
        if start_time:
            base_sql += " AND o.create_time >= ?"
            params.append(start_time)
        if end_time:
            base_sql += " AND o.create_time <= ?"
            params.append(end_time)
        
        # 按创建时间倒序
        base_sql += " ORDER BY o.create_time DESC"
        
        # 执行查询
        results = db.execute(base_sql, params)
        logger.info(f"✅ 查询历史记录成功：共{len(results)}条")
        return results
    except Exception as e:
        logger.error(f"❌ 查询历史记录失败：{str(e)}", exc_info=True)
        return []

def delete_history_record(operation_id, delete_files=True):
    """
    删除历史记录
    :param operation_id: 操作ID
    :param delete_files: 是否删除对应的输出文件夹
    :return: 删除成功返回True，失败返回False
    """
    if not validate_operation_id(operation_id):
        logger.error("❌ 操作ID格式错误，删除失败")
        return False
    
    try:
        # 步骤1：查询输出文件夹路径
        query_sql = "SELECT output_dir FROM tianditu_operations WHERE operation_id = ?"
        record = db.execute(query_sql, [operation_id])
        output_dir = record[0]["output_dir"] if record else None
        
        # 步骤2：开启事务，删除所有关联表记录
        db.execute("BEGIN TRANSACTION", commit=False)
        
        # 删除子表记录
        tables = ["tile_metadata", "merged_maps", "analysis_results", "reports", "tianditu_operations"]
        for table in tables:
            delete_sql = f"DELETE FROM {table} WHERE operation_id = ?"
            db.execute(delete_sql, [operation_id], commit=False)
        
        # 提交事务
        db.conn.commit()
        logger.info(f"✅ 数据库记录删除成功（operation_id：{operation_id}）")
        
        # 步骤3：删除输出文件夹（可选）
        if delete_files and output_dir and os.path.exists(output_dir):
            shutil.rmtree(output_dir)
            logger.info(f"✅ 输出文件夹删除成功：{output_dir}")
        
        return True
    except Exception as e:
        # 回滚事务
        db.conn.rollback()
        logger.error(f"❌ 删除历史记录失败（事务回滚）：{str(e)}", exc_info=True)
        return False

def get_record_detail(operation_id):
    """
    获取单条记录的完整详情（含所有关联数据）
    """
    if not validate_operation_id(operation_id):
        return None
    try:
        # 查询瓦片数量
        tile_sql = "SELECT COUNT(*) as tile_count FROM tile_metadata WHERE operation_id = ?"
        tile_count = db.execute(tile_sql, [operation_id])[0]["tile_count"]
        
        # 查询主记录+关联数据
        main_detail = query_history_records(operation_id=operation_id)
        if not main_detail:
            return None
        
        # 补充瓦片数量
        main_detail[0]["tile_count"] = tile_count
        return main_detail[0]
    except Exception as e:
        logger.error(f"❌ 获取记录详情失败：{str(e)}", exc_info=True)
        return None

# 测试用例
if __name__ == "__main__":
    # 查询所有成功的记录
    records = query_history_records(status="success")
    print(f"成功的记录数：{len(records)}")
    
    # 示例：查询单条记录详情
    if records:
        detail = get_record_detail(records[0]["operation_id"])
        print(f"记录详情：{detail['operation_id']} - {detail['place_name']}")