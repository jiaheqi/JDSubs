# JDSubs 监控系统

一个基于Flask的监控系统，用于监控京东商品和天气信息。

## Huggingface部署指南

### 1. 准备工作

- 确保你有Huggingface账号
- 创建新的Space（选择Docker类型）

### 2. 配置说明

#### 环境变量配置

在Huggingface Space的Settings中配置以下环境变量：

- `PORT`: 应用端口号（默认7860）

#### 配置文件

部署前需要在`config.ini`中配置：

```ini
[Weather]
api_key = 你的高德天气API密钥
city_id = 城市编码
push_time = 08:00

[JD]
product_url = 商品URL

[Monitor]
check_interval = 60
notify_minutes_before = 5

[WxPusher]
token = 你的WxPusher Token
uids = []
```

### 3. 部署步骤

1. Fork本仓库到你的GitHub账号
2. 在Huggingface Space中选择Docker部署
3. 连接你的GitHub仓库
4. 配置必要的环境变量
5. 等待自动部署完成

### 4. 验证部署

访问以下接口检查部署状态：

- 健康检查：`/health`
- 主页：`/`

### 5. 注意事项

- 确保所有配置文件使用相对路径
- 配置文件中的敏感信息建议使用环境变量
- 定期检查日志确保服务正常运行

## API接口

- `/api/logs/<script_id>`: 获取脚本日志
- `/api/config`: 获取/更新配置
- `/api/start/<script_id>`: 启动脚本
- `/api/stop/<script_id>`: 停止脚本
- `/api/status/<script_id>`: 获取脚本状态
- `/wxpusher/callback`: WxPusher回调接口