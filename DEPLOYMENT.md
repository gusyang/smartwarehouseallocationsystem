# 部署指南 | Deployment Guide

## 🌐 部署选项 | Deployment Options

本应用可以部署到多个平台，以下是详细说明。

This application can be deployed to multiple platforms. Here are detailed instructions.

---

## 1️⃣ 本地部署 | Local Deployment

### 最简单的方式 | Easiest Way

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 运行应用
streamlit run app_v2.py
```

访问: http://localhost:8501

**优点 | Pros**:
- ✅ 完全免费
- ✅ 数据完全私密
- ✅ 无需互联网

**缺点 | Cons**:
- ❌ 只能本地访问
- ❌ 需要保持电脑运行

---

## 2️⃣ Streamlit Cloud (推荐) | Streamlit Cloud (Recommended)

### 免费托管，最简单部署 | Free Hosting, Simplest Deployment

**步骤 | Steps**:

1. **将代码上传到 GitHub**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin <your-github-repo>
   git push -u origin main
   ```

2. **访问 Streamlit Cloud**
   - 前往: https://streamlit.io/cloud
   - 用 GitHub 账号登录
   - Click "New app"

3. **配置部署**
   - Repository: 选择你的 GitHub 仓库
   - Branch: main
   - Main file path: app_v2.py
   - Click "Deploy"

4. **等待部署** (通常1-2分钟)

**结果**:
- 获得一个公开URL: `https://your-app-name.streamlit.app`
- 自动HTTPS加密
- 自动更新(推送到GitHub后)

**限制 | Limits**:
- 免费版: 1GB RAM, 1 CPU
- 足够处理中等规模问题
- Sufficient for medium-scale problems

**成本 | Cost**: 
- 免费！ | Free!
- 对于个人和小团队完全够用
- Perfect for individuals and small teams

---

## 3️⃣ Heroku 部署 | Heroku Deployment

### 适合需要更多资源的场景 | For scenarios requiring more resources

**准备文件**:

1. **创建 `Procfile`** (无扩展名):
   ```
   web: streamlit run app.py --server.port=$PORT --server.address=0.0.0.0
   ```

2. **创建 `setup.sh`**:
   ```bash
   mkdir -p ~/.streamlit/
   
   echo "\
   [server]\n\
   headless = true\n\
   port = $PORT\n\
   enableCORS = false\n\
   \n\
   " > ~/.streamlit/config.toml
   ```

3. **修改 `Procfile` 使用 setup.sh**:
   ```
   web: sh setup.sh && streamlit run app_v2.py
   ```

**部署步骤**:

```bash
# 1. 安装 Heroku CLI
# 访问: https://devcenter.heroku.com/articles/heroku-cli

# 2. 登录
heroku login

# 3. 创建应用
heroku create your-app-name

# 4. 部署
git push heroku main

# 5. 打开应用
heroku open
```

**成本 | Cost**:
- Hobby tier: $7/月 | $7/month
- 更多内存和CPU | More RAM and CPU
- 适合生产环境 | Suitable for production

---

## 4️⃣ Docker 容器化部署 | Docker Containerized Deployment

### 适合企业部署 | For Enterprise Deployment

**创建 `Dockerfile`**:

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# 复制文件
COPY requirements.txt .
COPY app.py .
COPY *.md .
COPY *.csv .

# 安装依赖
RUN pip install --no-cache-dir -r requirements.txt

# 暴露端口
EXPOSE 8501

# 健康检查
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

# 运行应用
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

**构建和运行**:

```bash
# 构建镜像
docker build -t warehouse-optimizer .

# 运行容器
docker run -p 8501:8501 warehouse-optimizer

# 访问
# http://localhost:8501
```

**推送到 Docker Hub**:

```bash
# 登录
docker login

# 打标签
docker tag warehouse-optimizer your-username/warehouse-optimizer:latest

# 推送
docker push your-username/warehouse-optimizer:latest
```

**优点 | Pros**:
- ✅ 环境一致性
- ✅ 易于扩展
- ✅ 可部署到任何支持Docker的平台

---

## 5️⃣ AWS EC2 部署 | AWS EC2 Deployment

### 完全控制的云部署 | Full Control Cloud Deployment

**步骤**:

1. **启动 EC2 实例**
   - AMI: Ubuntu 22.04
   - 实例类型: t2.small 或更大
   - 安全组: 开放端口 8501

2. **SSH 连接**
   ```bash
   ssh -i your-key.pem ubuntu@your-ec2-ip
   ```

3. **安装依赖**
   ```bash
   sudo apt update
   sudo apt install python3-pip git -y
   ```

4. **克隆代码**
   ```bash
   git clone <your-repo>
   cd warehouse_optimizer
   ```

5. **安装 Python 包**
   ```bash
   pip3 install -r requirements.txt
   ```

6. **后台运行** (使用 tmux 或 screen)
   ```bash
   # 安装 tmux
   sudo apt install tmux -y
   
   # 创建会话
   tmux new -s streamlit
   
   # 运行应用
   streamlit run app.py --server.port=8501 --server.address=0.0.0.0
   
   # 分离会话: Ctrl+B, 然后按 D
   # 重新连接: tmux attach -t streamlit
   ```

7. **配置域名** (可选)
   - 使用 Nginx 作为反向代理
   - 配置 SSL 证书(Let's Encrypt)

**Nginx 配置示例**:

```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

**成本估算 | Cost Estimate**:
- EC2 t2.small: ~$17/月 | ~$17/month
- 适合中等流量 | Suitable for medium traffic

---

## 6️⃣ Azure Web App 部署 | Azure Web App Deployment

### Microsoft 云平台 | Microsoft Cloud Platform

**准备**:

1. **创建 `startup.sh`**:
   ```bash
   python -m streamlit run app.py --server.port=8000 --server.address=0.0.0.0
   ```

2. **使用 Azure CLI**:
   ```bash
   # 登录
   az login
   
   # 创建资源组
   az group create --name warehouse-rg --location eastus
   
   # 创建 App Service Plan
   az appservice plan create --name warehouse-plan --resource-group warehouse-rg --sku B1 --is-linux
   
   # 创建 Web App
   az webapp create --name warehouse-optimizer --resource-group warehouse-rg --plan warehouse-plan --runtime "PYTHON|3.10"
   
   # 配置启动命令
   az webapp config set --name warehouse-optimizer --resource-group warehouse-rg --startup-file startup.sh
   
   # 部署代码
   az webapp up --name warehouse-optimizer --resource-group warehouse-rg
   ```

**成本 | Cost**:
- Basic tier (B1): ~$55/月 | ~$55/month
- 更适合企业级应用 | More suitable for enterprise apps

---

## 7️⃣ Google Cloud Run 部署 | Google Cloud Run Deployment

### 无服务器容器部署 | Serverless Container Deployment

**步骤**:

1. **确保有 Dockerfile** (见上面Docker部分)

2. **使用 gcloud CLI**:
   ```bash
   # 初始化
   gcloud init
   
   # 构建容器
   gcloud builds submit --tag gcr.io/your-project-id/warehouse-optimizer
   
   # 部署到 Cloud Run
   gcloud run deploy warehouse-optimizer \
     --image gcr.io/your-project-id/warehouse-optimizer \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated
   ```

**优点 | Pros**:
- ✅ 按使用付费 | Pay per use
- ✅ 自动扩展 | Auto-scaling
- ✅ 零流量时几乎不产生费用 | Nearly free with zero traffic

**成本 | Cost**:
- 每月前 200万请求免费 | First 2M requests free/month
- 之后: $0.40 per million requests
- 非常适合不确定流量的应用 | Perfect for apps with uncertain traffic

---

## 🔐 安全建议 | Security Recommendations

### 1. 环境变量 | Environment Variables

**不要硬编码敏感信息！**

**Don't hardcode sensitive information!**

在 Streamlit Cloud:
- Settings → Secrets
- 添加 TOML 格式配置

```toml
[passwords]
admin = "your-secure-password"

[api_keys]
google_maps = "your-api-key"
```

在代码中使用:
```python
import streamlit as st

password = st.secrets["passwords"]["admin"]
```

### 2. 认证 | Authentication

添加简单的密码保护:

```python
import streamlit as st

def check_password():
    def password_entered():
        if st.session_state["password"] == st.secrets["password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("Password", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("Password", type="password", on_change=password_entered, key="password")
        st.error("😕 Password incorrect")
        return False
    else:
        return True

if check_password():
    # 应用主逻辑
    st.title("Warehouse Optimizer")
    # ...
```

### 3. HTTPS

**生产环境必须使用 HTTPS！**

**Production must use HTTPS!**

- Streamlit Cloud: 自动提供
- Heroku: 自动提供
- EC2: 使用 Let's Encrypt + Nginx
- Cloud Run: 自动提供

---

## 📊 监控和日志 | Monitoring and Logging

### Streamlit Cloud

内置监控:
- 应用健康状态
- 资源使用情况
- 错误日志

### 自托管

添加日志:

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('warehouse_optimizer.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# 在关键位置添加日志
logger.info("Optimization started")
logger.error(f"Optimization failed: {error}")
```

---

## 🚀 性能优化建议 | Performance Optimization Tips

### 1. 缓存

```python
@st.cache_data
def load_data():
    # 加载数据
    pass

@st.cache_resource
def get_database_connection():
    # 数据库连接
    pass
```

### 2. 会话状态管理

```python
# 避免重复计算
if 'optimization_result' not in st.session_state:
    st.session_state.optimization_result = optimize()
```

### 3. 异步加载

对于大数据集，考虑使用进度条:

```python
import time

progress_bar = st.progress(0)
for i in range(100):
    # 执行任务
    time.sleep(0.01)
    progress_bar.progress(i + 1)
```

---

## 📋 部署前检查清单 | Pre-Deployment Checklist

- [ ] 测试所有功能在本地正常工作
- [ ] 移除调试代码和打印语句
- [ ] 检查所有敏感信息已移至环境变量
- [ ] 更新 README 文档
- [ ] 准备示例数据
- [ ] 测试不同屏幕尺寸的响应式设计
- [ ] 设置错误处理和用户友好的错误消息
- [ ] 配置日志记录
- [ ] 准备备份策略
- [ ] 文档化 API 密钥获取流程(如果有)

---

## 🆘 故障排除 | Troubleshooting

### 问题: ModuleNotFoundError

**解决**: 
```bash
pip install -r requirements.txt --force-reinstall
```

### 问题: Port already in use

**解决**:
```bash
# 更改端口
streamlit run app.py --server.port=8502

# 或杀死占用端口的进程
lsof -ti:8501 | xargs kill -9
```

### 问题: Memory limit exceeded

**解决**:
- 升级到更大的实例
- 优化数据加载(使用分批处理)
- 增加缓存使用

### 问题: Streamlit app is slow

**解决**:
- 检查是否过度使用 `st.rerun()`
- 使用 `@st.cache_data` 缓存数据
- 优化算法复杂度
- 考虑异步处理大任务

---

## 📞 获取帮助 | Getting Help

### Streamlit 社区
- 论坛: https://discuss.streamlit.io
- GitHub: https://github.com/streamlit/streamlit

### 文档
- Streamlit Docs: https://docs.streamlit.io
- Deploy Docs: https://docs.streamlit.io/streamlit-community-cloud/get-started

---

**祝部署顺利! | Happy Deploying! 🚀**
