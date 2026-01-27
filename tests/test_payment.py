import pytest
import time
import qrcode
import os
import platform
import subprocess
import allure
from config.config import env_config
from utils.exchange_handler import ExchangeHandler
from utils.refund_handler import RefundHandler


@allure.feature("💰 支付中心")
@allure.story("核心支付流程")
@pytest.mark.payment
class TestPayment:

    @allure.title("[{final_order_id}] {case_info[desc]}")
    @pytest.mark.parametrize("case_info", env_config.payment_cases)
    def test_pay_order(self, api_client, case_info, db):

        # ... (前置变量和解包逻辑保持不变) ...
        desc = case_info.get("desc")
        method = case_info.get("method")
        url = case_info.get("url")
        assert_type = case_info.get("assert_type")
        order_static_params = case_info.get("params", {})
        enable_exchange = case_info.get("enable_exchange_flow", False)

        print(f"\n\n>>> 正在测试: {desc}")

        if assert_type == "pending":
            pytest.skip(f"【SKIPPED】{desc} 尚未开发")

        custom_headers = None
        final_order_id = None
        final_qr_content = None

        # ==========================================
        #  阶段一：POS 登录
        # ==========================================
        if "POS" in desc or "pos" in url.lower():
            with allure.step(f"步骤1: POS 终端登录"):
                pos_conf = env_config.pos_config
                login_res = api_client.post(pos_conf.get("login_url"), json=pos_conf.get("login_params", {}))
                assert login_res.status_code == 200, f"POS登录失败: {login_res.text}"

                token = login_res.json().get("content", {}).get("token") or login_res.json().get("Token")
                allure.attach(str(login_res.json()), name="POS登录返回", attachment_type=allure.attachment_type.JSON)
                assert token, "登录成功但未找到 Token"

                header_key = pos_conf.get("token_header_key", "Token")
                # 这里的 custom_headers 仅供 POS 支付接口使用
                custom_headers = {header_key: token}

        # ==========================================
        #  阶段二：执行支付
        # ==========================================
        with allure.step("步骤2: 发起支付请求"):
            final_payload = order_static_params
            allure.attach(str(final_payload), name="请求参数", attachment_type=allure.attachment_type.JSON)

            # 场景 A: POST 请求 (POS、员工卡)
            if method == "POST":
                if custom_headers:
                    print("  -> [POST] 使用 POS 专用 Token")
                    res = api_client.post(url, json=final_payload, headers=custom_headers)
                else:
                    print("  -> [POST] 使用 全局常规 Token")
                    # 员工卡等虽然是 POST，但用的是常规 Token (自动带入)
                    res = api_client.post(url, json=final_payload)

            # 场景 B: GET 请求 (微信、支付宝)
            elif method == "GET":
                print("  -> [GET] 使用 全局常规 Token (Params 传参)")
                # GET 请求通常不带 body，参数放在 URL query string 里
                # api_client.get 会自动带上全局 Token
                res = api_client.get(url, params=final_payload)

            else:
                pytest.fail(f"不支持的请求方法: {method}")

        # ==========================================
        #  阶段三：接口断言
        # ==========================================
        with allure.step("步骤3: 校验接口返回结果"):
            assert res.status_code == 200, f"HTTP状态码错误: {res.text}"
            res_json = res.json()
            allure.attach(str(res_json), name="接口响应", attachment_type=allure.attachment_type.JSON)

            server_order_id = res_json.get("OrderId") or res_json.get("data", {}).get("orderId")

            if not server_order_id:
                err_msg = res_json.get("CnMessage") or "未知错误"
                pytest.fail(f"❌ 下单失败: {err_msg}")

            final_order_id = server_order_id
            final_qr_content = res_json.get("PaymentQRCode")

            if assert_type == "check_qrcode" and not final_qr_content:
                pytest.fail("❌ 未返回二维码")

        # ==========================================
        #  阶段四：二维码展示
        # ==========================================
        if final_qr_content:
            with allure.step("步骤4: 展示二维码"):
                print(f"🔗 二维码内容: {final_qr_content}")
                self._process_qr_code(final_qr_content)

        # ==========================================
        #  阶段五：数据库校验
        # ==========================================
        with allure.step("步骤5: 数据库核对"):
            time.sleep(0.5)
            table_name = env_config.db_config.get("order_table_name", "[Order]")
            field_name = env_config.db_config.get("order_field_name", "[Id]")
            sql = f"SELECT * FROM {table_name} WHERE {field_name} = '{final_order_id}'"
            db_result = db.fetch_one(sql)
            allure.attach(str(db_result), name="DB查询结果", attachment_type=allure.attachment_type.TEXT)
            assert db_result is not None, f"❌ 数据库未找到订单"
            print(f"✅ 数据库校验通过！\n{db_result}")


        # ==========================================
        #  阶段六：执行兑换接口
        # ==========================================
        if enable_exchange:
            # 这样 handler 内部调用接口时，会使用 api_client 默认的常规 Token
            handler = ExchangeHandler(api_client, db)
            handler.process_exchange(final_order_id)
            refund_handler = RefundHandler(api_client, db)
            refund_handler.process_refund(final_order_id)

        print(f"\n{'=' * 15} ✅ {desc} 测试通过 {'=' * 15}")

    def _process_qr_code(self, data):
        # ... (保持不变) ...
        try:
            qr = qrcode.QRCode(border=4)
            qr.add_data(data)
            qr.make(fit=True)
            filename = f"qr_{int(time.time())}.png"
            abs_path = os.path.abspath(filename)
            img = qr.make_image(fill_color="black", back_color="white")
            img.save(filename)
            with open(filename, "rb") as f:
                allure.attach(f.read(), name="扫码支付", attachment_type=allure.attachment_type.PNG)
            system_name = platform.system()
            if system_name == "Windows":
                os.startfile(filename)
            elif system_name == "Darwin":
                subprocess.Popen(["open", filename])
            elif system_name == "Linux":
                subprocess.Popen(["xdg-open", filename])
        except Exception:
            pass