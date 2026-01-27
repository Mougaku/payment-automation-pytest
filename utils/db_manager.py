import pymssql  # <--- 变动 1：导入 pymssql
import logging
from config.config import env_config

logger = logging.getLogger(__name__)


class DBManager:
    def __init__(self):
        self.conf = env_config.db_config
        self.conn = None
        self.cursor = None

        try:
            # <--- 变动 2：连接参数调整
            self.conn = pymssql.connect(
                server=self.conf.get("host"),
                port=self.conf.get("port", 1433),  # 默认 1433
                user=self.conf.get("user"),
                password=self.conf.get("password"),
                database=self.conf.get("database"),
                charset=self.conf.get("charset", "utf8")
            )

            # <--- 变动 3：设置返回字典格式 (as_dict=True)
            self.cursor = self.conn.cursor(as_dict=True)
            logger.info("✅ SQL Server 数据库连接成功")
        except Exception as e:
            logger.error(f"❌ 数据库连接失败: {e}")
            raise e

    def fetch_one(self, sql, params=None):
        """
        支持参数化查询
        :param sql: SQL 语句 (使用 %s 作为占位符)
        :param params: 参数元组
        """
        try:
            logger.info(f"[SQL查询] {sql} | 参数: {params}")
            # execute 的第二个参数就是用来传值的，pymssql 会自动处理转义
            self.cursor.execute(sql, params)
            result = self.cursor.fetchone()
            return result
        except Exception as e:
            logger.error(f"SQL执行报错: {e}")
            raise e

    def close(self):
        """关闭连接"""
        try:
            if self.conn:
                self.conn.close()  # pymssql 关闭连接也会自动关闭 cursor
                logger.info("数据库连接已关闭")
        except Exception as e:
            logger.error(f"关闭连接报错: {e}")

