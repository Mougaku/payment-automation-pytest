import requests
import json
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)


class ApiClient:
    def __init__(self, base_url):
        self.base_url = base_url
        self.session = requests.Session()

    def request(self, method, endpoint, **kwargs):
        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"

        logger.info(f"\n>>> REQUEST: {method} {url}")
        # ... (日志部分保持不变)

        try:
            # 1. 发起请求
            response = self.session.request(method, url, **kwargs)

            # =============== 核心修复代码 START ===============
            # 检查响应内容是否以 BOM (Byte Order Mark) 开头
            # 如果是，强制将编码设置为 utf-8-sig，这样 json() 解析时会自动忽略 BOM
            if response.content.startswith(b'\xef\xbb\xbf'):
                response.encoding = 'utf-8-sig'
            else:
                # 否则强制设为 utf-8，防止中文乱码
                response.encoding = 'utf-8'
            # =============== 核心修复代码 END =================

            logger.info(f"<<< RESPONSE: Status {response.status_code}")
            try:
                # 这里的 response.json() 之前会报错，现在有了上面的修复就不会了
                logger.info(f"    DATA: {json.dumps(response.json(), ensure_ascii=False)}")
            except:
                logger.info(f"    DATA: {response.text[:100]}...")

            return response

        except Exception as e:
            logger.error(f"请求异常: {e}")
            raise e

    # get, post 方法保持不变...
    def get(self, endpoint, **kwargs):
        return self.request("GET", endpoint, **kwargs)

    def post(self, endpoint, **kwargs):
        return self.request("POST", endpoint, **kwargs)