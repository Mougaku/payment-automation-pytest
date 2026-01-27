import time
import pytest
import allure
from config.config import env_config


class RefundHandler:
    """
    负责处理退款业务 (Refund)
    """

    def __init__(self, api_client, db):
        self.api_client = api_client
        self.db = db
        self.table_name = env_config.db_config.get("order_table_name", "[Order]")
        self.field_id = env_config.db_config.get("order_field_name", "[Id]")
        self.refund_conf = env_config._config.get("refund_config", {})

    def process_refund(self, order_id):
        """执行退款流程：调用接口 -> 校验DB"""
        print(f"\n{'=' * 10} ↩️ 进入退款流程 {'=' * 10}")

        # 1. 调用退款接口
        self._call_refund_api(order_id)

        # 2. 校验数据库退款状态
        self._verify_refund_db_status(order_id)

    def _call_refund_api(self, order_id):
        with allure.step("步骤9: 执行退款接口 (AliPayRefundJob)"):
            url = self.refund_conf.get("url")
            params = {"orderId": order_id}

            print(f"  -> [Action] 发起退款请求: {url} | Params: {params}")

            res = self.api_client.get(url, params=params)
            allure.attach(str(res.status_code), name="退款接口原始响应", attachment_type=allure.attachment_type.TEXT)
            assert res.status_code == 204, f"退款接口报错: {res.status_code}"
            print(f"✅ 退款请求发送成功 (HTTP 200)，服务端未返回内容 (Empty Body)，视为成功。")

    def _verify_refund_db_status(self, order_id):
        """轮询检查数据库 [OrderRefundStatus] 是否变为 1"""

        target_field = "[OrderRefundStatus]"
        expected_val = "1"

        timeout = self.refund_conf.get("timeout_seconds", 30)
        interval = self.refund_conf.get("poll_interval", 3)
        max_retries = int(timeout / interval)

        with allure.step(f"步骤10: 校验数据库退款状态 ({target_field} == {expected_val})"):
            is_refunded = False

            # 轮询 5 次，每次 3 秒
            for i in range(1, max_retries + 1):
                print(f"  -> [退款轮询 {i}/{max_retries}] 查询 {target_field}...")

                sql = f"SELECT {target_field} FROM {self.table_name} WHERE {self.field_id} = '{order_id}'"
                db_result = self.db.fetch_one(sql)

                if db_result:
                    # 注意去除方括号获取 key
                    status = db_result.get("OrderRefundStatus")
                    print(f"     当前状态: {status}")

                    if str(status) == expected_val:
                        print("  ✅ 数据库状态确认：退款成功！")
                        is_refunded = True
                        allure.attach(f"轮询成功，状态为 {status}", name="DB校验结果")
                        break

                time.sleep(interval)

            if not is_refunded:
                err_msg = f"❌ 退款校验失败: 15秒内 {target_field} 未变更为 {expected_val}。OrderId: {order_id}"
                print(err_msg)
                # 这是一个硬性校验，如果不通过则报错
                pytest.fail(err_msg)