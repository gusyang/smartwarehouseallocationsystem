# 部署指南

## 1. 本地测试

```bash
# 安装依赖
pip install -r requirements.txt

# 运行测试
streamlit run app_v2.py
```

## 2. 推送到 GitHub

```bash
git add .
git commit -m "Add SQLite persistence and SKU/Carrier management"
git push origin main
```

## 3. Streamlit Cloud 设置

1. 登录 https://share.streamlit.io
2. 选择你的 GitHub 仓库
3. 设置:
   - Main file path: `app_v2.py`
   - Python version: 3.8+
4. 点击 Deploy

## 4. 重要说明

### SQLite 持久化原理

Streamlit Cloud 每个 session 会重启，**但是**：
- SQLite 数据库文件 (`warehouse_optimizer.db`) 会保存在 repo 中
- 每次 git push 后，数据库文件会保持

**注意**: 首次部署后，需要在界面上操作一次来创建数据库文件。

### 数据持久化流程

1. 应用启动时 → 从 SQLite 加载数据到 session_state
2. 用户修改数据 → 保存到 SQLite + 更新 session_state  
3. 刷新页面 → 从 SQLite 重新加载

### 数据库文件位置

数据库文件存储在应用目录:
```
Warehouse-optimizer/
├── app_v2.py
├── db.py
└── warehouse_optimizer.db  (自动创建)
```

### 备份建议

定期导出数据库:
```bash
# 导出
sqlite3 warehouse_optimizer.db ".backup backup.db"

# 或者通过界面导出为 JSON/Excel
```

## 5. 故障排除

**问题**: 数据库文件不存在
**解决**: 首次运行应用后，数据库会自动创建

**问题**: 数据不更新
**解决**: 点击页面刷新按钮，或重启应用

**问题**: 需要重置数据
**解决**: 删除 `warehouse_optimizer.db` 文件，重新部署
