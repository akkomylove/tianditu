"""
数据库工具类 - 新增事务+重试机制（阶段4改造版）
✅ 单例模式 + 通用CRUD + 异常处理
✅ 新增：事务装饰器、重试装饰器、更严格的参数校验
"""
import sqlite3
import logging
import threading
import time
from functools import wraps
from datetime import datetime
from config import DB_TYPE, DB_PATH, DB_TIMEOUT

# 配置日志（输出到文件+控制台，更详细）
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s",
    handlers=[
        logging.FileHandler("tianditu_db.log", encoding="utf-8"),  # 日志写入文件
        logging.StreamHandler()  # 控制台输出
    ]
)
logger = logging.getLogger("db_utils")

# ========== 新增：重试装饰器（数据库写入失败自动重试） ==========
def retry_on_failure(max_retries=3, delay=1, exceptions=(sqlite3.Error,)):
    """
    重试装饰器：指定异常发生时，自动重试指定次数
    :param max_retries: 最大重试次数（默认3次）
    :param delay: 重试间隔（默认1秒）
    :param exceptions: 触发重试的异常类型（默认SQLite错误）
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    retries += 1
                    logger.warning(f"❌ 执行失败（重试{retries}/{max_retries}）：{str(e)}")
                    if retries >= max_retries:
                        logger.error(f"❌ 达到最大重试次数（{max_retries}次），执行失败")
                        raise  # 抛出最终异常
                    time.sleep(delay)
            return None
        return wrapper
    return decorator

# ========== 新增：事务装饰器（确保原子性） ==========
def with_transaction(func):
    """
    事务装饰器：执行函数时开启事务，成功则提交，失败则回滚
    """
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if not self._check_connection():
            return None
        try:
            self.conn.execute("BEGIN TRANSACTION")  # 开启事务
            result = func(self, *args, **kwargs)
            self.conn.commit()  # 提交事务
            logger.info("✅ 事务提交成功")
            return result
        except Exception as e:
            self.conn.rollback()  # 回滚事务
            logger.error(f"❌ 事务执行失败，已回滚：{str(e)}", exc_info=True)
            return None
    return wrapper

class DatabaseUtils:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._connect()
        return cls._instance

    def _connect(self):
        try:
            if DB_TYPE.lower() == "sqlite":
                self.conn = sqlite3.connect(
                    DB_PATH,
                    timeout=DB_TIMEOUT,
                    check_same_thread=False
                )
                self.conn.row_factory = sqlite3.Row
                self.cursor = self.conn.cursor()
                logger.info(f"✅ 数据库连接成功（SQLite）：{DB_PATH}")
            else:
                raise NotImplementedError(f"暂不支持数据库类型：{DB_TYPE}")
        except Exception as e:
            logger.error(f"❌ 数据库连接失败：{str(e)}", exc_info=True)
            self.conn = None
            self.cursor = None

    def _check_connection(self):
        if not self.conn:
            logger.warning("⚠️ 数据库连接已断开，尝试重新连接...")
            self._connect()
        return self.conn is not None

    # ========== 改造：执行SQL时添加参数校验 + 重试 ==========
    @retry_on_failure(max_retries=3, delay=1)
    def execute(self, sql, params=None, commit=False):
        if not self._check_connection():
            return None
        params = params or ()
        # 新增：参数类型校验（避免非预期类型）
        try:
            # 检查SQL占位符数量和参数数量匹配
            placeholder_count = sql.count("?")
            if placeholder_count != len(params):
                raise ValueError(f"SQL占位符数量（{placeholder_count}）与参数数量（{len(params)}）不匹配")
        except Exception as e:
            logger.error(f"❌ SQL参数校验失败：{str(e)}", exc_info=True)
            return None
        
        try:
            logger.debug(f"执行SQL：{sql} | 参数：{params}")
            self.cursor.execute(sql, params)
            if commit:
                self.conn.commit()
                logger.debug(f"✅ 事务提交成功，影响行数：{self.cursor.rowcount}")
                return self.cursor.rowcount
            else:
                results = [dict(row) for row in self.cursor.fetchall()]
                logger.debug(f"✅ 查询成功，返回行数：{len(results)}")
                return results
        except sqlite3.IntegrityError as e:
            logger.error(f"❌ 数据库完整性错误（主键重复/约束冲突）：{str(e)}", exc_info=True)
            if commit:
                self.conn.rollback()
                logger.warning("⚠️ 事务回滚")
            return None
        except Exception as e:
            logger.error(f"❌ 执行SQL失败：{str(e)}", exc_info=True)
            if commit:
                self.conn.rollback()
                logger.warning("⚠️ 事务回滚")
            raise  # 抛出异常，让重试装饰器处理

    # ========== 改造：批量插入添加事务 + 重试 ==========
    @with_transaction  # 新增：批量插入用事务包裹
    @retry_on_failure(max_retries=3, delay=1)
    def batch_insert(self, sql, params_list, batch_size=100):
        if not self._check_connection() or not params_list:
            return 0
        total_count = 0
        # 新增：批量参数校验
        for params in params_list:
            placeholder_count = sql.count("?")
            if placeholder_count != len(params):
                logger.error(f"❌ 批量参数校验失败：单条参数数量（{len(params)}）与占位符数量（{placeholder_count}）不匹配")
                return 0
        
        try:
            for i in range(0, len(params_list), batch_size):
                batch_params = params_list[i:i+batch_size]
                self.cursor.executemany(sql, batch_params)
                batch_count = len(batch_params)
                total_count += batch_count
                logger.debug(f"✅ 批量插入成功：第{i//batch_size+1}批，{batch_count}条")
            logger.info(f"✅ 批量插入完成，总条数：{total_count}")
            return total_count
        except Exception as e:
            logger.error(f"❌ 批量插入失败：{str(e)}", exc_info=True)
            raise  # 抛出异常，触发事务回滚

    def get_current_time(self):
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def close(self):
        if self.conn:
            self.conn.close()
            logger.info("✅ 数据库连接已关闭")
            self.conn = None
            self.cursor = None

# 创建全局实例
db = DatabaseUtils()

# 测试用例
if __name__ == "__main__":
    if db.conn:
        result = db.execute("SELECT name FROM sqlite_master WHERE type='table'")
        logger.info(f"当前数据库表：{[item['name'] for item in result]}")
    else:
        logger.error("❌ 测试失败：数据库连接无效")