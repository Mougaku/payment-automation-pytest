import time
import pytest
import allure
import copy
from datetime import datetime, timedelta
from config.config import env_config


class ExchangeHandler:
    """
    专门负责处理兑换（SyncSalesData）相关的复杂业务逻辑
    包含：数据库轮询、动态参数计算、接口调用
    """

    def __init__(self, api_client, db):
        self.api_client = api_client
        self.db = db
        # 读取配置
        self.table_name = env_config.db_config.get("order_table_name", "[Order]")
        self.field_id = env_config.db_config.get("order_field_name", "[Id]")
        self.exchange_conf = env_config._config.get("exchange_config", {})
        self.redeem_table = env_config.db_config.get("redeem_table_name", "[RedeemDetail]")
        self.redeem_field = env_config.db_config.get("redeem_field_name", "[OrderId]")

    def process_exchange(self, order_id):
        """
        执行完整的兑换流程
        :param order_id: 支付成功的订单ID
        """
        print(f"\n{'=' * 10} 🚦 进入兑换流程 (请手动扫码支付) {'=' * 10}")

        # 1. 轮询数据库状态
        self._poll_db_status(order_id)

        # 2. 调用兑换接口
        self._call_exchange_api(order_id)

        # 3. ▼▼▼ 新增：兑换数据落地校验 ▼▼▼
        self._verify_redeem_db(order_id)

    def _poll_db_status(self, order_id):
        """内部方法：轮询数据库支付状态"""
        # 【优化】步骤名称改为 步骤6
        with allure.step("步骤6: 轮询数据库支付状态"):
            is_paid = False

            timeout = self.exchange_conf.get("timeout_seconds", 50)  # 默认50秒
            interval = self.exchange_conf.get("poll_interval", 5)  # 默认5秒
            max_retries = int(timeout / interval)

            # 【修改点 1】轮询从 6 次改为 10 次 (range(1, 11))
            print(f"  -> [配置] 最大等待 {timeout}s, 轮询间隔 {interval}s, 共 {max_retries} 次")

            for i in range(1, max_retries + 1):
                # 【修改点 2】日志和 SQL 中的字段改为 [OrderPaymentStatus]
                print(f"  -> [轮询 {i}/{max_retries}] 正在查询数据库 [OrderPaymentStatus]...")

                # 注意：SQL Server 中带方括号是标准的引用方式
                sql = f"SELECT [OrderPaymentStatus] FROM {self.table_name} WHERE {self.field_id} = '{order_id}'"
                db_result = self.db.fetch_one(sql)

                if db_result:
                    # 获取结果。通常 pymssql 返回的字典 key 不带方括号，所以这里用 "OrderPaymentStatus"
                    # 如果你的数据库驱动返回的 key 带括号，请改为 db_result.get("[OrderPaymentStatus]")
                    payment_status = db_result.get("OrderPaymentStatus")
                    print(f"     当前状态: {payment_status}")

                    # 判断状态是否为 1
                    if str(payment_status) == "1":
                        print("  ✅ 检测到支付成功！")
                        is_paid = True
                        allure.attach(f"第 {i} 次轮询成功，状态为 1", name="轮询结果")
                        break

                time.sleep(interval)

            if not is_paid:
                # 错误信息也同步修改
                err_msg = f"❌ 超时错误: 50秒内数据库 [OrderPaymentStatus] 未变更为 1。Order ID: {order_id}"
                print(err_msg)
                pytest.fail(err_msg)

    def _call_exchange_api(self, order_id):
        """内部方法：计算动态参数并调用兑换接口"""
        # 【优化】步骤名称改为 步骤7
        with allure.step("步骤7: 执行兑换接口"):
            print("  -> [Action] 计算动态参数并调用兑换接口...")

            url = self.exchange_conf.get("url")
            # 1. 【关键】使用 deepcopy 深拷贝整个静态参数结构
            # 因为是多层嵌套 (dict -> list -> dict)，普通的 .copy() 是浅拷贝，会改乱配置
            final_payload = copy.deepcopy(self.exchange_conf.get("static_params", {}))

            # 2. 定位到要修改的那个内部对象 (redeemData 列表的第一个元素)
            try:
                target_item = final_payload["redeemData"][0]
            except (KeyError, IndexError):
                pytest.fail("❌ 配置文件错误: exchange_config.static_params 缺少 redeemData 数组或数组为空")

            # ==========================================
            # ▼▼▼ 动态参数注入 ▼▼▼
            # ==========================================

            # 1. orderId
            target_item["orderId"] = order_id

            # 2. expiryDate
            future_date = datetime.now() + timedelta(days=30)
            target_item["expiryDate"] = future_date.strftime("%d%m%y")

            # 3. redeemDateTime
            current_date_str = datetime.now().strftime("%Y%m%d")
            target_item["redeemDateTime"] = f"{current_date_str}111111"

            # ==========================================

            print(f"     生成的动态参数: orderId={order_id}, time={target_item['redeemDateTime']}")
            allure.attach(str(final_payload), name="兑换接口完整参数", attachment_type=allure.attachment_type.JSON)

            # 发起请求 (final_payload 已经是完整的结构了，直接传)
            res = self.api_client.post(url, json=final_payload)
            res_json = res.json()

            allure.attach(str(res.json()), name="兑换接口响应", attachment_type=allure.attachment_type.JSON)

            # 1. 基础 HTTP 校验 (依然保留，防止 404/500 等服务器错误)
            assert res.status_code == 200, f"兑换接口 HTTP 异常: {res.status_code}"

            # 2. 业务逻辑校验 (校验 CnMessage)
            actual_msg = res_json.get("CnMessage")
            expected_msg = "数据同步成功"

            if actual_msg != expected_msg:
                # 如果不匹配，抛出详细错误，方便在报告里看
                # 有些接口可能叫 message 或者 msg，这里根据你的实际情况只校验 CnMessage
                fail_reason = f"❌ 业务返回失败!\n期望: {expected_msg}\n实际: {actual_msg}\n完整响应: {res_json}"
                print(fail_reason)
                pytest.fail(fail_reason)
            print("✅ 兑换接口调用成功！")

    def _verify_redeem_db(self, order_id):
        """内部方法：校验兑换数据是否落库"""
        with allure.step("步骤8: 兑换数据落库校验 (RedeemDetail)"):
            print(f"  -> [DB校验] 正在查询兑换明细表: {self.redeem_table}")

            # 构造 SQL
            # 假设表里的字段名就叫 OrderId (如果不一样请修改这里)
            sql = f"SELECT * FROM {self.redeem_table} WHERE {self.redeem_field} = '{order_id}'"

            allure.attach(sql, name="执行SQL语句", attachment_type=allure.attachment_type.TEXT)

            # 执行查询
            db_result = self.db.fetch_one(sql)

            allure.attach(str(db_result), name="DB查询结果", attachment_type=allure.attachment_type.TEXT)

            # 断言
            if not db_result:
                fail_msg = f"❌ 严重错误: 兑换接口返回成功，但在 {self.redeem_table} 表中未找到 OrderId={order_id} 的记录"
                print(fail_msg)
                pytest.fail(fail_msg)

            print(f"✅ 兑换数据校验通过！已找到记录: {db_result}")