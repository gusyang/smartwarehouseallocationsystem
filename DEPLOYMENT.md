# 部署指南 | Deployment Guide

## 本地运行 | Local Development

```bash
# 安装依赖
pip install -r requirements.txt

# 运行应用
streamlit run app_v2.py
```

访问: http://localhost:8501

---

## Streamlit Cloud 部署 | Streamlit Cloud Deployment

### 1. 推送代码到GitHub

```bash
git add .
git commit -m "Add SQLite, SKU, Carrier & Vehicle management"
git push origin main
```

### 2. 部署

1. 登录 https://share.streamlit.io
2. 选择你的 GitHub 仓库
3. 设置:
   - Main file path: `app_v2.py`
   - Python version: 3.8+
4. 点击 Deploy

### 3. 首次运行

首次部署后，访问应用会自动创建SQLite数据库文件(`warehouse_v5.db`)。

---

## SQLite 数据库 | SQLite Database

### 持久化原理

- 数据库文件存储在应用目录中
- 每次部署后数据会保持
- **注意**: 首次访问需要操作一次来初始化默认数据

### 备份

```bash
# 本地复制数据库
copy warehouse_v5.db backup_warehouse_v5.db
```

### 重置数据

如需重置为默认数据:
1. 删除 `warehouse_v5.db` 文件
2. 刷新页面

---

## 故障排除 | Troubleshooting

| 问题 | 解决方案 |
|------|----------|
| 数据库锁定 | 删除 `warehouse_v5.db` 文件，重启应用 |
| 数据不更新 | 刷新页面 |
| 需要重置数据 | 删除数据库文件，刷新页面 |

---

## 项目文件

```
Warehouse-optimizer/
├── app_v2.py           # 主应用
├── db.py               # SQLite模块
├── requirements.txt    # 依赖
├── .gitignore          # Git忽略配置
└── warehouse_v5.db     # 数据库(运行时创建)
```
