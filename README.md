# Payment Automation Framework

基于 Pytest + Allure 的支付全链路自动化测试框架。

## 核心功能
* ✅ **全流程覆盖**：下单 -> 扫码支付 -> 数据库校验 -> 兑换 -> 退款。
* ✅ **多渠道支持**：支持 POS、Alipay、WeChat 等多种支付方式。
* ✅ **稳健设计**：包含轮询机制、断言重试、数据库防延迟处理。
* ✅ **可视化报告**：集成 Allure 测试报告。

## 目录结构
* `tests/`: 测试用例脚本
* `utils/`: 核心工具类 (DB, API, Handlers)
* `config/`: 配置文件

## 快速开始
1. 安装依赖: `pip install -r requirements.txt`
2. 配置环境: 复制 `config/dev.json.example` 为 `config/dev.json` 并填入数据库信息。
3. 运行测试: `pytest`
