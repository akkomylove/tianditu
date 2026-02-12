"""
数据库初始化脚本 - 自动创建所有数据表
✅ 检查表是否存在，不存在则创建
✅ 支持字段约束、外键关联、级联删除
✅ 可重复执行（仅创建不存在的表）
"""
from db_utils import db, logger
def create_tables():
    """创建所有数据表"""
    # 1. 操作主表（tianditu_operations）
    create_operations_table = """
    CREATE TABLE IF NOT EXISTS tianditu_operations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        operation_id VARCHAR(32) UNIQUE NOT NULL,
        place_name VARCHAR(128) NOT NULL,
        tile_type VARCHAR(32) NOT NULL,
        zoom_level INTEGER NOT NULL CHECK(zoom_level BETWEEN 1 AND 18),
        min_lon FLOAT(10,6) NOT NULL CHECK(min_lon BETWEEN 73.0 AND 135.0),
        max_lon FLOAT(10,6) NOT NULL CHECK(max_lon BETWEEN 73.0 AND 135.0),
        min_lat FLOAT(10,6) NOT NULL CHECK(min_lat BETWEEN 4.0 AND 53.0),
        max_lat FLOAT(10,6) NOT NULL CHECK(max_lat BETWEEN 4.0 AND 53.0),
        output_dir VARCHAR(256) NOT NULL,
        status VARCHAR(16) DEFAULT 'running' CHECK(status IN ('running', 'success', 'failed')),
        create_time DATETIME NOT NULL,
        update_time DATETIME NOT NULL,
        is_deleted TINYINT DEFAULT 0
    );
    """
    # 2. 瓦片信息表（tile_metadata）
    create_tile_metadata_table = """
    CREATE TABLE IF NOT EXISTS tile_metadata (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        operation_id VARCHAR(32) NOT NULL,
        tile_x INTEGER NOT NULL,
        tile_y INTEGER NOT NULL,
        tile_z INTEGER NOT NULL CHECK(tile_z BETWEEN 1 AND 18),
        tile_path VARCHAR(256) NOT NULL,
        download_status VARCHAR(16) DEFAULT 'success' CHECK(download_status IN ('success', 'failed')),
        create_time DATETIME NOT NULL,
        update_time DATETIME NOT NULL,
        is_deleted TINYINT DEFAULT 0,
        FOREIGN KEY (operation_id) REFERENCES tianditu_operations(operation_id) ON DELETE CASCADE
    );
    """
    # 3. 拼接地图表（merged_maps）
    create_merged_maps_table = """
    CREATE TABLE IF NOT EXISTS merged_maps (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        operation_id VARCHAR(32) NOT NULL UNIQUE,
        merged_path VARCHAR(256) NOT NULL,
        width INTEGER NOT NULL CHECK(width > 0),
        height INTEGER NOT NULL CHECK(height > 0),
        file_size INTEGER NOT NULL CHECK(file_size > 0),
        create_time DATETIME NOT NULL,
        update_time DATETIME NOT NULL,
        is_deleted TINYINT DEFAULT 0,
        FOREIGN KEY (operation_id) REFERENCES tianditu_operations(operation_id) ON DELETE CASCADE
    );
    """
    # 4. 分析结果表（analysis_results）- 最终修改：删除INDEX行，适配SQLite
    create_analysis_results_table = """
    CREATE TABLE IF NOT EXISTS analysis_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        operation_id TEXT NOT NULL UNIQUE, -- 操作唯一标识，SQLite自动为UNIQUE建索引
        -- 交通类（原有+新增）
        total_traffic_poi INTEGER DEFAULT 0 CHECK(total_traffic_poi >= 0),
        traffic_density FLOAT(8,2) DEFAULT 0.00,
        traffic_convenience_score FLOAT(3,1) DEFAULT 0.0,
        traffic_poi_detail TEXT DEFAULT '{}',
        traffic_type_ratio TEXT DEFAULT '{}',
        -- 文化类（原有+新增）
        total_culture_poi INTEGER DEFAULT 0 CHECK(total_culture_poi >= 0),
        culture_density FLOAT(8,2) DEFAULT 0.00,
        culture_feature_score FLOAT(3,1) DEFAULT 0.0,
        culture_poi_detail TEXT DEFAULT '{}',
        culture_type_ratio TEXT DEFAULT '{}',
        -- 生活服务类（新增）
        total_life_poi INTEGER DEFAULT 0 CHECK(total_life_poi >= 0),
        life_density FLOAT(8,2) DEFAULT 0.00,
        life_convenience_score FLOAT(3,1) DEFAULT 0.0,
        life_poi_detail TEXT DEFAULT '{}',
        -- 商业设施类（新增）
        total_commercial_poi INTEGER DEFAULT 0 CHECK(total_commercial_poi >= 0),
        commercial_density FLOAT(8,2) DEFAULT 0.00,
        commercial_activity_score FLOAT(3,1) DEFAULT 0.0,
        commercial_poi_detail TEXT DEFAULT '{}',
        -- 教育设施类（新增）
        total_education_poi INTEGER DEFAULT 0 CHECK(total_education_poi >= 0),
        education_density FLOAT(8,2) DEFAULT 0.00,
        education_support_score FLOAT(3,1) DEFAULT 0.0,
        education_poi_detail TEXT DEFAULT '{}',
        -- 医疗设施类（新增）
        total_medical_poi INTEGER DEFAULT 0 CHECK(total_medical_poi >= 0),
        medical_density FLOAT(8,2) DEFAULT 0.00,
        medical_support_score FLOAT(3,1) DEFAULT 0.0,
        medical_poi_detail TEXT DEFAULT '{}',
        -- 交叉分析（新增）
        insights TEXT DEFAULT '[]',
        -- 通用字段
        create_time TEXT NOT NULL,
        update_time TEXT NOT NULL
    );
    """
    # 5. 报告表（reports）
    create_reports_table = """
    CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        operation_id VARCHAR(32) NOT NULL UNIQUE,
        report_path VARCHAR(256) NOT NULL,
        generate_status VARCHAR(16) DEFAULT 'success' CHECK(generate_status IN ('success', 'failed')),
        create_time DATETIME NOT NULL,
        update_time DATETIME NOT NULL,
        is_deleted TINYINT DEFAULT 0,
        FOREIGN KEY (operation_id) REFERENCES tianditu_operations(operation_id) ON DELETE CASCADE
    );
    """
    # 执行创建语句
    tables_sql = [
        (create_operations_table, "操作主表"),
        (create_tile_metadata_table, "瓦片信息表"),
        (create_merged_maps_table, "拼接地图表"),
        (create_analysis_results_table, "分析结果表"),
        (create_reports_table, "报告表")
    ]
    for sql, table_name in tables_sql:
        try:
            result = db.execute(sql, commit=True)
            if result is not None:
                logger.info(f"✅ {table_name}创建成功（或已存在）")
            else:
                logger.error(f"❌ {table_name}创建失败")
        except Exception as e:
            logger.error(f"❌ {table_name}创建异常：{str(e)}", exc_info=True)
if __name__ == "__main__":
    logger.info("="*50)
    logger.info("🌍 开始初始化天地图分析工具数据库")
    logger.info("="*50)
    create_tables()
    logger.info("="*50)
    logger.info("🌍 数据库初始化完成")
    logger.info("="*50)