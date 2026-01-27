import json
import os
from pathlib import Path

# 获取 config 目录路径
BASE_DIR = Path(__file__).parent.parent
CONFIG_DIR = BASE_DIR / "config"


class ConfigLoader:
    def __init__(self):
        # 1. 获取环境变量 TEST_ENV
        # os.getenv("变量名", "默认值")
        # 如果没设置变量，默认跑 dev 环境
        self.env = os.getenv("TEST_ENV", "dev").lower()

        print(f"\n=================================")
        print(f" 🚀 当前运行环境: {self.env}")
        print(f"=================================")

        self._config = self._load_config()

    def _load_config(self):
        # 2. 动态拼接文件名：dev.json, stage.json ...
        file_path = CONFIG_DIR / f"{self.env}.json"

        if not file_path.exists():
            # 如果输错了环境名（比如 set TEST_ENV=abc），直接报错提示
            raise FileNotFoundError(f"配置文件未找到: {file_path} (请检查 TEST_ENV 变量)")

        # 保持 utf-8-sig 以防止 BOM 问题
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            return json.load(f)

    @property
    def host(self):
        return self._config.get("host")

    @property
    def token(self):
        return self._config.get("auth", {}).get("token")

    @property
    def payment_cases(self):
        return self._config.get("payment_cases", [])

    @property
    def pos_config(self):
        """读取配置文件里的 pos_config 字段"""
        return self._config.get("pos_config", {})

    @property
    def db_config(self):
        return self._config.get("db_config", {})

# 实例化
env_config = ConfigLoader()