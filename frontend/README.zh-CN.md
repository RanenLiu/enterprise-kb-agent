# 前端 — 企业知识库智能问答

React 19 + Shadcn Admin + Vite + Tailwind v4 管理后台。

## 技术栈

| 分类 | 选型 |
|------|------|
| **框架** | React 19, TypeScript (strict) |
| **构建** | Vite, Tailwind v4 |
| **组件** | Shadcn Admin (Radix UI), Lucide 图标 |
| **路由** | react-router-dom v7, 懒加载 |
| **主题** | 深色/浅色模式 + 5 种强调色 + 毛玻璃效果 |
| **通知** | sonner (toast) |
| **HTTP** | fetch 基础 API 客户端 |

## 快速开始

### 前置条件

- Node.js ≥ 20
- pnpm ≥ 8
- 后端 API 运行在 `http://localhost:8000`

### 安装 & 运行

```bash
cd frontend
pnpm install
pnpm dev
```

打开 [http://localhost:5173](http://localhost:5173)。

### 生产构建

```bash
pnpm build
```

输出到 `dist/`，可用 Nginx 或任何静态服务器部署。

## 配置

### API 地址

前端通过相对路径 `/api/v1/xxx` 请求后端：

- **开发模式**：Vite proxy → `http://localhost:8000`
- **Docker 模式**：Nginx proxy → `http://backend:8000`

无需修改代码即可切换环境。

## 页面路由

| 路由 | 页面 | 说明 |
|------|------|------|
| `/login` | 登录 | 认证 |
| `/chat` | 智能问答 | SSE 流式对话 |
| `/chat/:id` | 对话详情 | 会话历史 |
| `/knowledge` | 知识库 | 文档管理 |
| `/admin/departments` | 部门管理 | CRUD、成员管理 |
| `/admin/roles` | 角色管理 | CRUD、权限分配 |
| `/admin/users` | 用户管理 | CRUD、角色分配 |
| `/admin/logs` | 操作日志 | 审计记录（操作 & 登录） |
| `/admin/models` | 模型配置 | LLM 模型设置 |
| `/admin/settings` | 系统设置 | 系统配置 |

## UI 特性

- **深色/浅色模式**：主题切换
- **毛玻璃设计**：全局 frosted glass 风格
- **响应式**：移动端适配，侧栏可收起
- **流式聊天**：SSE 实时响应
- **RBAC 菜单**：按角色自动过滤
- **验证码**：失败登录后强制验证
- **EP 工号**：新建用户自动生成

## UI 框架

**Shadcn Admin** 是一个基于 [shadcn/ui](https://ui.shadcn.com/) 的开源管理后台模板（shadcn/ui 底层使用 [Radix UI](https://www.radix-ui.com/) 无样式原语）。组件自带无障碍支持，通过 Tailwind 自定义样式，没有自带的设计系统约束。

**Tailwind v4** 是 Tailwind CSS 的最新大版本。它引入了 CSS 优先的配置方式（`@theme` 指令）、原生 CSS 级联层、以及自动内容检测。主题色使用 OKLCH 色彩空间，色相变化均匀，渐变更自然。

与 v3 的关键区别：Tailwind v4 不再需要 `tailwind.config.js`，所有主题变量在 CSS 的 `@theme inline {}` 块中定义，由 Vite 插件即时生成样式。
