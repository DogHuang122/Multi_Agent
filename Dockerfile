# 1. 指定基础“房车”底盘：这里我们选一个带 Python 3.10 的轻量级官方环境
FROM python:3.10-slim

# 2. 在房车里建一个工作目录叫 /app
WORKDIR /app

# 3. 先把依赖清单复制进房车
COPY requirements.txt .

# 4. 让房车里的系统安装这些依赖
# --no-cache-dir 是为了不留安装缓存，让打包出来的体积更小
RUN pip install --no-cache-dir -r requirements.txt

# 5. 把你当前文件夹下的所有代码（main.py, index.html, 各种 Agent 脚本）统统复制到房车的 /app 目录里
COPY . .

# 6. 告诉 Docker，这个程序要在 8000 端口对外提供服务
EXPOSE 8000

# 7. 房车启动时，默认执行的命令 (注意去掉了 reload，因为正式环境不需要热更新)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]