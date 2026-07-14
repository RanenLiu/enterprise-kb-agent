# 变更日志

## [未发布]

### 新增
- LlamaIndex 检索管线: HuggingFaceEmbedding(bge-m3) + SentenceTransformerRerank，替代自定义向量检索和重排
- 检索增强策略: HyDE(假设文档嵌入)、QueryFusion(多视角查询)、StepDecomp(多步分解)，config 开关控制
- BM25 中文重排回归: jieba 分词在 RRF 融合后重打分，防止 RRF 摊平精确匹配
- 严格模式: knowledge_query 无有效结果(score<0.2)时返回"未找到"，不依赖 LLM 自有知识
- 闲聊不检索: general_chat 意图自动跳过知识库搜索，不展示检索来源
- 来源阈值过滤: score<0.2 的 chunk 不展示"相关文档"区域
- 相关文档标签: 引用来源/相关文档/检索来源 三态合并为统一的"相关文档"
- 会话列表多选删除: 后端 batch-delete + 前端 checkbox 批量选择
- 公告 scope 前缀: system/tenant/dept 三级，显示 [系统]/[租户名]/[部门] 标签
- 无标题文件智能分块: TXT/CSV/EML/XLSX 按段落→句子递归分块，支持跨 chunk overlap
- 多轮检索缓存: Redis 3 轮 LRU，query embedding 余弦相似度匹配，支持代词消解
- BM25 中文检索评分: 纯 Python 实现，RRF 融合后重打分，jieba 分词 + 停用词过滤
- MMR 多样性选择模块: Jaccard 相似度 + λ 参数控制相关/多样平衡
- 意图置信度追问: 置信度 < 0.7 时 LLM 自动追问用户确认意图
- 来源分组折叠: 按文档分组，默认收起，点击展开查看详情
- `content_tsv` 列 + PG 触发器: 支持 tsvector 全文检索（英文生效，中文降级 ILIKE）
- `OFFICE_EXTENSIONS` 增加 `.ppt` 和 `.xls` 支持
- 文档解析: DOCX 标题样式（Heading 1/2/3）转为 Markdown 标题
- 文档解析: PPTX 区分标题/正文，标题前加 `#` 标记

### 修复
- React 19 style 异常: style prop 传字符串改为对象（error #62）
- PGSearch 参数 bug: project_ids 误传入 top_k 参数（企业版全文检索 top_k 长期损坏）
- Docker CUDA 依赖: OS Dockerfile 先装 CPU torch，避免 sentence-transformers 拉 CUDA 版
- 登录密码长度: LoginRequest 去掉 min_length=6，登录只校验匹配
- 验证码红边框: 验证码错误时用户名/密码不加红边框
- 聊天字体颜色: 统一 text-foreground（Light=黑，Dark=白）
- 用户气泡背景: bg-primary/15→/20，AI 气泡 bg-muted→/70
- 长文本换行: 添加 break-words，pre 代码块 white-space:pre-wrap
- 气泡宽度: max-w-[75%]→[60%]
- 无会话时隐藏输入区域
- Office 预览提示统一: 所有预览统一显示下载提示（后端生成的 HTML 内部已包含，前端不再重复）
- 用户不能改自己角色: 编辑自己时角色 checkbox 禁用
- 首页去 GraphRAG: 开源版首页去掉企业版内容
- 文档可见范围: 仅超管/租户管/部门管可修改，dept_editor/dept_viewer 不可修改
- 文档删除/重索引: 仅所有者和超管/租户管可见操作按钮
- [object Object] 错误提示: 前端 client.ts 处理 `json.detail` 为数组时逐条提取 `.msg`（OS + Enterprise）
- ILIKE 全给 0.5 分无区分度: BM25 替换固定分，按词频+逆文档频率重算相关分
- 来源污染（显示无关文档）: 按文档总分选 top doc 替代 MMR 多样性选取
- 后续轮次检索错文档: 跨轮 doc_context 存取 + 三层 doc_ids 注入
- xlsx 内容检索不到: parser 去掉 `read_only=True`（`data_only=True` 冲突 bug）
- xlsx/pptx 预览崩溃: `_PREVIEW_BANNER` 变量名不一致、`_convert_pptx_to_html` 签名缺 `download_url` 参数
- SSE 公告连接被拦截: Announcement SSE 去除 URL 中 token 参数，与 `/knowledge/status/events` 统一的免认证模式
- 后端验证错误中文提示: 新增 `RequestValidationError` 处理器，Pydantic 校验错误（string_too_short/missing 等）自动返回中文（三入口：OS/Enterprise/信创）
- 会话主题生成: LLM 提示改为中文短语格式
- 上传租户图片 500: storage_client 导入方式修复（from...import → import...as）
- 保存品牌设置登出: 开源版增加 PUT /admin/tenant 端点
- 部门管理员用户菜单缺失: seed 脚本增加系统管理子菜单
- 部门管理员越权查看文档: visibility 过滤层（private/dept/public）
- 部门查看者权限过大: menu 移除知识库入口（保留 document.read）
- 全链路 RBAC 审查: 补充 chat.access、departments/my 角色检查、dept_editor reindex 权限
- 检索 pipeline 空 dept_ids 导致公共文档搜不到: `if not dept_ids: return []` 修复
- 检索 pipeline `hybrid_search` 不接收 project_ids 导致 TypeError: 签名同步修复
- 检索 pipeline `r.chunk_id` 属性访问但 search() 返回 dict 导致 AttributeError: 改为 dict 访问
- 检索 pipeline content_tsv 列缺失导致 ILIKE 兜底不执行: try/except + rollback 修复
- 检索 pipeline intent 为 knowledge_query 时仍跳过检索: jieba 分词代替硬编码关键词
- PDF 解析失败: 添加 PyMuPDF 依赖
- 管理员上传文档 dept_id=None 导致 worker 崩溃: queue.py/worker.py None 处理
- 登录错误显示 "Request failed": 前端读 json.detail 显示正确错误信息
- 登录失败自动聚焦: 有验证码聚焦验证码，否则聚焦密码；输入框红色边框
- 用户创建不再要求输入密码: 默认 admin123
- 删除旧 backend/ 单体目录（19713 行死代码），迁移 .env 到 server/

### 变更
- Worker 模块化迁移: `server/backend/worker.py` 完全脱离旧 `app.*` 单体
- RabbitMQ 消费者适配器: `kb_adapter_rabbitmq.consumer`

### 变更
- worker entrypoint 从 `python -m app.worker` 改为 `python -m worker`（三套 compose 文件均已更新）
- 统一 Dockerfile 删除 `COPY backend/ /app/backend/`（232MB 老单体不再打包进镜像）
- 统一 Dockerfile 不再安装 `kb-adapter-neo4j`，OS worker 零 Neo4j 暴露
- Dockerfile 改为多阶段构建，清理 nvidia/cuda/triton 垃圾，镜像 5.82GB → 1.57GB
- 文档状态实时更新: Redis pub/sub + SSE 端点 `GET /knowledge/status/events`，替代轮询
- 开源版知识库页面移除"图谱"按钮
- 模块化架构重构: `server/packages/kb-core/` + `kb-biz/` + `kb-adapter-postgres/` + `kb-adapter-neo4j/` 四包结构
- 薄入口 `server/backend/main.py`: 组装 kb-biz 路由 + kb-adapter-postgres 会话
- 开源版资源硬限制: 30 用户 / 5 部门 / 150 文档 / 50MB 单文件

### 修复
- 操作日志 `display_name`: 关联 User 表获取当前名，用户删除后降级为存储名
- 失败登录记录 `user_id`，确保日志可追溯
- backend/README.md 重写（英文版，面向开源贡献者）
- frontend/README.md 重写（项目定制，替代默认 Vite 模板）
- docs/ARCHITECTURE.md 深度架构分析（9 章含设计决策对比表）
- Apache 2.0 LICENSE 文件
- 用户缓存(Redis Write-Through): 5 分钟 TTL，变更主动失效
- 文件上传 API: POST /admin/upload 图片上传到 MinIO（头像/Logo）
- 系统设置: 应用名称/Logo 自定义
- 管理员重置密码: PUT /admin/users/{id}/reset-password
- 会话标题自动生成: 首条消息 LLM 生成标题，Redis+PG 持久化
- LLM 配置部门级: 聊天优先部门级配置，fallback 全局
- 操作日志全面覆盖: 所有 CRUD 操作记录日志
- 种子数据角色中文名: 超级管理员/部门管理员/编辑者/查看者
- 部门管理员菜单裁剪: 去掉角色管理/菜单管理
- 统一新建按钮样式: 所有页面 `+ 新建xx` 风格
- 前端按钮点击动画: `@keyframes` 放大效果，不受 React 重渲染影响
- 侧边栏展开状态持久化: localStorage 存储，刷新保持
- 侧边栏菜单项间距: 18px margin，选中主题色背景
- 侧边栏收起宽度: 68px，右侧分割线移除
- 侧边栏 Logo 点击跳转首页
- 子菜单样式: margin-left 26px、border 移除、padding-left 13px
- 菜单项光标统一: 一级/二级菜单均为 `pointer`
- 移动端适配: 表格横向滚动、聊天页会话列表可收起、侧栏菜单底色
- 侧栏缩放手柄: 收起状态隐藏
- 手机端主题选择器: 改为左对齐避免溢出，选中 ring 标识
- 弹窗输入框: 聚焦时光标移到末尾，不选中全部内容
- 意图识别优化: 添加"你是谁"等闲聊示例，闲聊跳过工具选择
- 标题生成修复: 移回 done 事件前执行，确保前端加载时已就绪
- 项目名称统一: 企业知识库智能客服 → 企业知识库智能问答

### 变更
- 知识库上线开关: published(bool) → visibility(private/dept/public)
- 部门/用户删除: 硬删除改为软删除(status=0)

- 聊天列表删除: 逻辑删除(status="deleted")
- 列表统一分页组件: 每页条数选择 + 总数显示
- ConfirmDialog 替代原生 confirm
- button `cursor: pointer` 全局注入

### 修复
- 会话标题不生成: 移至 done 事件前执行
- 意图误判为 knowledge_query: 闲聊跳过 tool_selector
- 手机输入框自动放大: 设 font-size 16px + touch-action: manipulation
- 面包屑手机垂直显示: 窄屏隐藏
- 侧栏按钮手机透明: 加底色
- 聊天会话列表手机透明: 使用 sidebar-background 底色

## [0.1.0] — 2026-06-24

### 新增
- 项目初始化
- 架构设计文档（SDD）
- 工程规范（CLAUDE.md）
- 需求文档（requirements.md）
- CI/CD 权限配置（.claude/settings.local.json）

## [0.2.0] — 2026-06-24

### 新增
- docker-compose: PostgreSQL 16, Milvus v2.6.15, Redis 7.2, MinIO
- 后端骨架: FastAPI 入口, 配置管理, 结构化日志, 全局异常处理
- 数据模型: 用户/部门/角色/权限/文档/对话/日志(Alembic 迁移)
- Pydantic Schema: 认证/管理员/通用响应契约
- 核心基础设施: JWT 认证, bcrypt 密码, RBAC 权限定义
- API 路由: 认证(登录/注册/刷新/个人设置), 管理员(部门/角色/用户 CRUD), 对话(会话), 健康检查
- 前端: Vite + React 19 + TypeScript + shadcn/ui, 管理布局含侧边栏
- Seed 脚本: 默认权限/角色/超级管理员
- 开发脚本: setup_dev.sh 一键初始化
