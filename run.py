import os
import pytest
import shutil

# 定义报告数据的存放路径
REPORT_DIR = "./report"


def run():
    print("🧹 [1/3] 正在清理旧的测试报告数据...")
    # 为了防止历史数据干扰，每次运行前先清理掉 report 文件夹
    if os.path.exists(REPORT_DIR):
        shutil.rmtree(REPORT_DIR)

    print("🚀 [2/3] 开始执行 Pytest 测试...")
    # 相当于在命令行执行 pytest -s --alluredir=./report
    # 你可以在这里加更多的参数，比如 "-v" (详细模式)
    pytest.main(["-s", f"--alluredir={REPORT_DIR}"])

    print("\n📊 [3/3] 测试结束，正在自动打开 Allure 报告...")
    # 调用系统命令启动 allure 服务
    # 这会启动一个本地 Web Server 并自动打开默认浏览器
    os.system(f"allure serve {REPORT_DIR}")


if __name__ == '__main__':
    run()