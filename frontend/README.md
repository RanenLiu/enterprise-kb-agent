# Frontend — Enterprise Knowledge Base Agent

React 19 + Shadcn Admin + Vite + Tailwind v4 admin dashboard.

## Tech Stack

| Category | Libraries |
|----------|-----------|
| **Framework** | React 19, TypeScript (strict mode) |
| **Build** | Vite, Tailwind v4 |
| **UI Components** | Shadcn Admin (Radix UI), Lucide icons |
| **Routing** | react-router-dom v7 |
| **State** | Zustand-style stores |
| **Markdown** | react-markdown + remark-gfm |
| **Themes** | next-themes (dark/light), Glassmorphism design |
| **Notifications** | sonner (toast) |
| **HTTP** | fetch-based API client |

## Project Structure

```
frontend/
├── src/
│   ├── main.tsx                  # App entry point
│   ├── App.tsx                   # Router & layout configuration
│   ├── api/
│   │   └── client.ts             # API client with JWT handling
│   ├── pages/
│   │   ├── LoginPage.tsx         # Authentication
│   │   ├── ChatPage.tsx          # Intelligent QA interface
│   │   ├── KnowledgePage.tsx     # Knowledge base management
│   │   ├── KnowledgeGraphPage.tsx # Graph visualization
│   │   ├── DashboardPage.tsx     # System dashboard
│   │   └── admin/                # Admin pages
│   │       ├── users/            # User CRUD
│   │       ├── departments/      # Department CRUD
│   │       ├── roles/            # Role & permission CRUD
│   │       ├── menus/            # Menu management
│   │       ├── tenants/          # Multi-tenant management
│   │       ├── logs/             # Operation & login logs
│   │       └── monitor/          # System health monitoring
│   ├── components/               # Shared UI components
│   ├── hooks/                    # Custom React hooks
│   ├── stores/                   # State management
│   ├── layouts/                  # Layout components (sidebar, header)
│   ├── types/                    # TypeScript type definitions
│   └── utils/                    # Utility functions
├── package.json
├── vite.config.ts
└── README.md                     # This file
```

## Quick Start

### Prerequisites

- Node.js ≥ 20
- pnpm ≥ 8
- Backend API running at `http://localhost:8000`

### Install & Run

```bash
cd frontend
pnpm install
pnpm dev
```

Opens at [http://localhost:5173](http://localhost:5173).

### Build for Production

```bash
pnpm build
```

Output goes to `dist/`. Serve with any static file server or Nginx.

## Configuration

### API Base URL

The frontend reads `VITE_API_BASE_URL` from environment (defaults to `http://localhost:8000`):

```bash
# .env.local
VITE_API_BASE_URL=http://localhost:8000
```

### Connecting to a Different Backend

Since the project uses an API-contract architecture, you can point the frontend at any backend that implements the OpenAPI contract.

```bash
VITE_API_BASE_URL=https://api.your-company.com
```

## Available Scripts

| Command | Description |
|---------|-------------|
| `pnpm dev` | Start dev server with HMR |
| `pnpm build` | Production build |
| `pnpm preview` | Preview production build locally |
| `pnpm lint` | Run Oxlint |

## Pages

| Route | Page | Description |
|-------|------|-------------|
| `/login` | Login | Authentication |
| `/chat` | Chat | Intelligent QA with streaming |
| `/chat/:id` | Chat Detail | Conversation history |
| `/knowledge` | Knowledge Base | Document management |
| `/admin/departments` | Department Management | CRUD, member management |
| `/admin/roles` | Role Management | CRUD, permission assignment |
| `/admin/users` | User Management | CRUD, role assignment |
| `/admin/logs` | Operation Logs | Audit trail (operations & login) |
| `/admin/models` | Model Config | LLM model settings |
| `/admin/settings` | System Settings | System configuration |

## UI Features

- **Dark/Light Mode**: Theme toggle with `next-themes`
- **Glassmorphism Design**: Frosted glass aesthetic throughout
- **Responsive**: Fully mobile-adapted — collapsible sidebar, scrollable tables
- **Streaming Chat**: Real-time SSE-based response streaming
- **RBAC Menus**: Navigation menus filtered by user role
- **Toast Notifications**: Action feedback via `sonner`
- **Markdown Rendering**: Chat responses rendered with react-markdown + GFM

## UI Framework

**Shadcn Admin** is an open-source admin dashboard template built on [shadcn/ui](https://ui.shadcn.com/) (which itself wraps [Radix UI](https://www.radix-ui.com/) primitives). It provides accessible, unstyled components that you customize via Tailwind — no opinionated design system to fight against.

**Tailwind v4** is the latest major version of the utility-first CSS framework. It introduces CSS-first configuration (the `@theme` directive), native CSS cascade layers, and automatic content detection. Theme colors use OKLCH color space for perceptually uniform gradients and accent hues.

Key difference from v3: Tailwind v4 no longer uses `tailwind.config.js` — all theme variables are defined in `@theme inline {}` blocks in CSS, and utilities are generated on-the-fly by the Vite plugin.
