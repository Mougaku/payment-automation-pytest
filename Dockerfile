# 1. 使用官方 Python 3.10 轻量版作为基础镜像
FROM python:3.10-slim

# 2. 设置维护者信息 (可选)
LABEL maintainer="YourName <your@email.com>"

# 3. 设置环境变量 (防止 Python 生成 .pyc 文件，让日志直接输出)
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 4. 设置工作目录
WORKDIR /app

# 5. 安装系统依赖 (pymssql 在 Linux 需要 freetds)
# 这一步对于连接 SQL Server 至关重要
RUN apt-get update && apt-get install -y \
    freetds-dev \
    freetds-bin \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 6. 复制依赖清单并安装
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 7. 复制项目所有代码到镜像中
COPY . .

# 8. (可选) 声明容器运行时需要挂载的卷 (配置和报告)
# 这一步只是为了提示使用者，不写也可以
VOLUME ["/app/config", "/app/report", "/app/allure-results"]

# 9. 容器启动时的默认命令 (直接运行测试)
CMD ["pytest"]