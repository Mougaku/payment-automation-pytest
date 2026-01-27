import pytest
from utils.api_client import ApiClient
from utils.db_manager import DBManager
from config.config import env_config
import os     # 新增
import glob   # 新增

@pytest.fixture(scope="session")
def auth_token():
    """从配置读取 Token"""
    token = env_config.token
    if not token:
        raise ValueError("Token未配置")
    return token


@pytest.fixture(scope="session")
def api_client(auth_token):
    """初始化客户端，并自动注入 Token"""
    client = ApiClient(base_url=env_config.host)

    # 设置公共请求头
    client.session.headers.update({
        "Tower_Authorization": auth_token,
        "Content-Type": "application/json"
    })
    return client

@pytest.fixture(scope="session")
def db():
    """
    数据库连接 Fixture
    scope="session" 表示整个测试过程只连一次数据库，测试全部结束后断开
    """
    try:
        db_mgr = DBManager()
        yield db_mgr
    finally:
        # 测试结束后自动关闭连接
        db_mgr.close()


@pytest.fixture(scope="session", autouse=True)
def cleanup_qr_files():
    """
    会话级夹具：在所有测试开始前什么都不做，
    在所有测试结束后，自动清理根目录下的 qr_*.png 文件
    """
    # yield 之前是 Setup（测试前），这里留空
    yield

    # yield 之后是 Teardown（测试后），执行清理
    print("\n🧹 [Cleanup] 开始清理临时二维码图片...")

    # 查找所有以 qr_ 开头，.png 结尾的文件
    qr_files = glob.glob("qr_*.png")

    if not qr_files:
        print("   ✅ 没有发现残留的二维码文件。")
        return

    for file_path in qr_files:
        try:
            os.remove(file_path)
            print(f"   🗑️ 已删除: {file_path}")
        except Exception as e:
            # 这里的报错通常是因为图片正被你看图软件打开着，导致被占用无法删除
            # 我们选择忽略这个错误，不影响测试结果
            print(f"   ⚠️ 无法删除 {file_path} (可能文件被占用): {e}")