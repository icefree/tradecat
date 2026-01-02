# 贡献指南

感谢你对 TradeCat 项目的关注！

## 开发环境

### 环境要求

- Python 3.10+
- TimescaleDB (端口 5433)
- TA-Lib (系统库)

### 初始化

```bash
# 克隆仓库
git clone https://github.com/tukuaiai/tradecat.git
cd tradecat

# 一键安装
./install.sh

# 或手动初始化
./scripts/init-all.sh
```

## 开发流程

### 1. 创建分支

```bash
git checkout -b feature/your-feature
# 或
git checkout -b fix/your-fix
```

### 2. 开发

```bash
# 激活虚拟环境
source services/<service>/.venv/bin/activate

# 修改代码
# ...

# 运行验证
./scripts/verify.sh
```

### 3. 提交

```bash
git add .
git commit -m "feat(scope): description"
```

### 4. 推送

```bash
git push origin feature/your-feature
```

## Commit 规范

```
<type>(<scope>): <subject>
```

### Type

| Type | 说明 |
|:---|:---|
| `feat` | 新功能 |
| `fix` | Bug 修复 |
| `docs` | 文档更新 |
| `refactor` | 重构 |
| `test` | 测试 |
| `chore` | 杂项 |

### Scope

- `data`: data-service
- `trading`: trading-service
- `telegram`: telegram-service
- `order`: order-service
- `docs`: 文档

### 示例

```
feat(trading): 添加 K线形态检测指标
fix(telegram): 修复排行榜数据加载错误
docs: 更新 README 快速开始指南
```

## 代码规范

- 遵循 PEP 8
- 关键函数添加类型注解
- 公开函数需有 docstring
- 使用 ruff 格式化（如有）

## 文档同步

修改以下内容时，必须同步更新文档：

| 变更类型 | 需更新 |
|:---|:---|
| 新增/修改命令 | README.md, AGENTS.md |
| 新增/修改配置项 | README.md, .env.example |
| 新增/修改指标 | README.md |
| 目录结构变更 | README.md, AGENTS.md |

## 联系方式

- Telegram: [@glue_coding](https://t.me/glue_coding)
- Twitter: [@123olp](https://x.com/123olp)
