FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 复制项目文件
COPY . /app/

# 安装依赖
RUN pip install --no-cache-dir -r requirements.txt

# 设置环境变量
ENV PORT=7860

# 暴露端口
EXPOSE ${PORT}

# 启动命令
CMD ["python", "app.py", "--port", "${PORT}"]