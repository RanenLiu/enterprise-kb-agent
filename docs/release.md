# 发布流程

## 仓库架构

- **私有库**（`origin`）— 完整版，包含 OS + 企业版 + 信创版代码，日常开发
- **公开库**（`public`）— 只含 OS 文件，接受社区 PR

```
私有库 develop ──发布──→ 公开库 main
     ↑                        │
     └──── cherry-pick PR ────┘
```

> 命名规则：默认名 = 开源版，企业版/信创版带后缀标识（`.enterprise.` / `.xc.`）。

## 文件归属

```
enterprise-kb-agent/
│
├── [公开] README.md                       # OS README（英文）
├── [公开] README.zh-CN.md                 # OS README（中文）
├── [公开] CHANGELOG.md                    # OS 变更日志
├── [公开] LICENSE                         # Apache 2.0
├── [公开] .gitignore
├── [公开] .dockerignore
├── [公开] docker-compose.yml              # OS Docker 编排
│
├── [私有] CHANGELOG-enterprise.md         # 企业版变更日志（含 OS 条目）
├── [私有] CLAUDE.md                       # 项目指令（含企业版引用）
├── [私有] README.enterprise.md/zh-CN.md   # 企业版 README
├── [私有] README.xc.md/zh-CN.md           # 信创版 README
├── [私有] README.overview.md/zh-CN.md     # 统一概览页
├── [私有] docker-compose.enterprise.yml   # 企业版 Docker 编排
├── [私有] docker-compose.xc.yml           # 信创版 Docker 编排
│
├── [私有] .claude/                        # 本地 CLI 配置（密钥/权限）
│
├── [私有] data/                           # Docker 卷数据（非 Git 管理）
│
├── docs/
│   ├── [公开] ARCHITECTURE.md/zh-CN.md    # OS 架构文档
│   ├── [公开] llm-config.md/zh-CN.md      # LLM 配置指南
│   │
│   ├── [私有] ARCHITECTURE.enterprise.*    # 企业版架构
│   ├── [私有] ARCHITECTURE.xc.*           # 信创版架构
│   ├── [私有] release.md                  # 发布流程（本文件）
│   ├── [私有] review-findings.md          # 审查记录
│   ├── [私有] roadmap.md                  # 路线图
│   ├── [私有] experience.md               # 踩坑记录
│   ├── [私有] requirements.md             # 需求文档
│   ├── [私有] sdd/                        # 架构设计文档
│   ├── [私有] superpowers/                # AI 辅助工作记录
│   └── [私有] credentials.md / test-cases.md / neo4j-queries.md / ...
│
├── server/
│   ├── [公开] README.md                   # OS 后端 README
│   ├── [公开] backend/                    # OS FastAPI 入口
│   ├── [公开] packages/kb-core/           # AI 引擎（LLM/RAG/解析/索引）
│   ├── [公开] packages/kb-biz/            # 业务逻辑（API/模型/认证）
│   ├── [公开] packages/kb-adapter-postgres/ # PostgreSQL 适配器
│   ├── [公开] packages/kb-adapter-rabbitmq/ # RabbitMQ 适配器
│   ├── [公开] scripts/seed_os.py          # OS 种子数据
│   ├── [公开] scripts/reset-env.sh
│   ├── [公开] scripts/setup_dev.sh
│   ├── [公开] scripts/add_content_tsv.sql
│   ├── [公开] scripts/migrate_001_content_tsv.py
│   │
│   ├── [私有] README.enterprise.md        # 企业版后端 README
│   ├── [私有] backend-enterprise/         # 企业版 FastAPI 入口
│   ├── [私有] backend-xc/                 # 信创版 FastAPI 入口
│   ├── [私有] packages/kb-enterprise/     # 企业功能包
│   ├── [私有] packages/kb-core-enterprise/ # 企业 AI 扩展
│   ├── [私有] packages/kb-adapter-neo4j/  # Neo4j 适配器
│   ├── [私有] packages/kb-adapter-dameng/ # 达梦适配器
│   ├── [私有] packages/kb-adapter-nebula/ # NebulaGraph 适配器
│   ├── [私有] packages/kb-adapter-rocketmq/ # RocketMQ 适配器
│   └── [私有] scripts/seed_enterprise.py  # 企业版种子
│   └── [私有] scripts/create_test_users.py / generate_test_data.py
│
└── frontend/
    ├── [公开] README.md / README.zh-CN.md  # 前端 README
    ├── [公开] src/ / public/ / package.json / Dockerfile / ...
    │
    ├── [私有] enterprise/                 # 企业版前端代码
    └── [私有] Dockerfile.enterprise       # 企业版 Dockerfile
```

## 仓库命名

建议两个公开库用统一名称，例如 `enterprise-kb-agent`（简短且不易截断）。

## 添加公开库 remote

```bash
# GitHub
git remote add public https://github.com/RanenLiu/enterprise-kb-agent.git
```

## 发布到公开库

从 `develop` 创建孤儿分支，只签出 OS 文件，推送到公开库 `main`：

```bash
# 1. 确保 develop 是最新
git checkout develop
git pull origin develop

# 2. 创建孤儿分支（空工作区、无历史），并确认已切换
git checkout --orphan os-release && test "$(git branch --show-current)" = "os-release" && echo "OK: 已在 os-release 分支" || echo "ERROR: 切换失败，请重试"

# 3. 从 develop 只签出 OS 文件
#    根目录
git checkout develop -- \
  README.md \
  README.zh-CN.md \
  LICENSE \
  CHANGELOG.md \
  .gitignore \
  .dockerignore \
  docker-compose.yml

#    文档（仅入公开库的部分）
git checkout develop -- \
  docs/ARCHITECTURE.md \
  docs/ARCHITECTURE.zh-CN.md \
  docs/architecture-overview.html \
  docs/architecture-overview.zh-CN.html \
  docs/retrieval-pipeline.html \
  docs/retrieval-pipeline.zh-CN.html \
  docs/agent-pipeline.html \
  docs/agent-pipeline.zh-CN.html \
  docs/llm-config.md \
  docs/llm-config.zh-CN.md

#    架构图 PNG
git checkout develop -- docs/diagrams/

#    后端（开源入口 + 开源包）
git checkout develop -- \
  server/backend/ \
  server/packages/kb-core/ \
  server/packages/kb-biz/ \
  server/packages/kb-adapter-postgres/ \
  server/packages/kb-adapter-rabbitmq/ \
  server/scripts/reset-env.sh \
  server/scripts/seed_os.py \
  server/scripts/setup_dev.sh \
  server/scripts/add_content_tsv.sql \
  server/scripts/migrate_001_content_tsv.py \
  server/README.md

#    前端（完整，排除 enterprise/ 目录）
git checkout develop -- frontend/

# 4. 清理企业版/信创版/环境文件（按命名规则通配删除）
rm -rf \
  frontend/enterprise/ \
  frontend/Dockerfile.enterprise \
  frontend/node_modules/ \
  frontend/dist/ \
  server/backend-enterprise/ \
  server/backend-xc/ \
  server/packages/kb-enterprise/ \
  server/packages/kb-core-enterprise/ \
  server/packages/kb-adapter-neo4j/ \
  server/packages/kb-adapter-dameng/ \
  server/packages/kb-adapter-nebula/ \
  server/packages/kb-adapter-rocketmq/ \
  server/scripts/seed_enterprise.py \
  server/scripts/create_test_users.py \
  server/scripts/generate_test_data.py \
  server/scripts/__init__.py \
  server/.env \
  .claude/ \
  data/ \
  .vscode/

# 5. 清理残留的企业版/信创版文档（按文件名模式匹配）
find . -type f \( -name "*.enterprise.*" -o -name "*.xc.*" -o -name "CHANGELOG-enterprise*" -o -name "CLAUDE.md" -o -name "README.overview*" \) -delete 2>/dev/null
find docs/ -type f \( -name "credentials*" -o -name "experience*" -o -name "review-findings*" -o -name "roadmap*" -o -name "requirements*" -o -name "test-cases*" -o -name "neo4j-queries*" -o -name "pitch-template*" \) -delete 2>/dev/null
rm -rf docs/ops/ docs/sdd/ docs/superpowers/ 2>/dev/null
echo "清理完成"

# 6. 提交并推送
git add -A
git commit -m "release: v$(date +%Y.%m.%d)"
git push public os-release:main

# 7. 回到 develop，清理临时分支
git checkout develop
git branch -D os-release
```

## 拉取社区 PR

社区 PR 合入公开库 `main` 后，cherry-pick 到私有库 `develop`：

```bash
# 拉取公开库最新
git fetch public main

# cherry-pick PR 对应的 commit
git cherry-pick <commit-hash>
```

因为 PR 只涉及 OS 文件，私有库全都有，不会出现冲突。

## 注意事项

- 孤儿分支的 commit 完全独立于私有库历史，公开库看不到任何私有库的文件、commit message 或历史
- 不要在公开库 `main` 上直接修改企业文件——公开库本身就没有这些文件
- 企业版文件命名均带 `.enterprise.` 或 `.xc.` 后缀，不会被 `git checkout develop --` 漏带走
- frontend/enterprise/ 目录需手动清理（git checkout develop -- frontend/ 会包含它）
- `.claude/`（本地配置/密钥）和 `data/`（Docker 卷数据）明确不进入公开库，建议发布前检查确认
- 以下文档仅限私有库，不要在 OS 发布中包含：`docs/release.md`、`docs/review-findings.md`、`docs/roadmap.md`、`docs/sdd/`、`docs/superpowers/`、`docs/experience.md`

## Gitee 镜像同步

在 GitHub 公开库发布后，可在 Gitee 创建同名仓库并开启自动同步：

1. 在 [Gitee](https://gitee.com) 创建同名仓库（例如 `enterprise-kb-agent`）
2. 进入 Gitee 仓库 → **管理** → **仓库镜像管理**
3. 点击**添加镜像**，方向选「从 GitHub 同步」
4. 授权 Gitee 访问你的 GitHub 账号，填入 GitHub 公开库地址
5. Gitee 自动定期拉取更新，也可手动点「立即同步」

> 注意：Gitee 同步是**单向的**（GitHub → Gitee），PR 仍需在 GitHub 上处理。社区 PR 合入 GitHub 公开库后，先用 cherry-pick 拉回私有库 develop，Gitee 会自动同步更新。
