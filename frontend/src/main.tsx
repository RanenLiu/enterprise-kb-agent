import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { TooltipProvider } from '@/components/ui/tooltip'
import { ThemeProvider } from '@/hooks/useTheme'
import './index.css'
import App from './App.tsx'

// Inject global button styles (bypasses Tailwind CSS processing)
const _style = document.createElement('style')
_style.textContent = `@keyframes btn-click { 0%{transform:scale(1)} 25%{transform:scale(1.05)} 100%{transform:scale(1)} }
button:not(:disabled) { cursor: pointer; }
[data-slot="sidebar-menu-button"],[data-slot="sidebar-menu-sub-button"] { cursor: pointer; }
[data-slot="sidebar-menu-button"] { margin-left: 18px; margin-right: 18px; }
[data-slot="sidebar-menu-sub"]{margin-left:26px!important;border-left:none!important;padding-left:13px!important}
[data-slot="sidebar-menu-button"][data-active="true"]{background:color-mix(in srgb,var(--primary) 12%,transparent)!important;color:var(--primary)!important}
[data-slot="sidebar-menu-sub-button"][data-active="true"]{background:color-mix(in srgb,var(--primary) 12%,transparent)!important;color:var(--primary)!important}
@media(max-width:768px){
[data-sidebar="trigger"]{opacity:1!important;color:var(--foreground)!important;background:var(--accent)!important;border-radius:6px;border:1px solid var(--border)!important}
[data-slot="sidebar-menu-button"],[data-slot="sidebar-menu-sub-button"]{background:var(--sidebar-background)!important}
[data-sidebar="sidebar"][data-mobile="true"]{background:var(--background)!important}
header nav{display:none!important}
.admin-table .table-scroll{overflow-x:auto!important;-webkit-overflow-scrolling:touch!important;height:auto!important;max-height:60vh}
.admin-table table{table-layout:auto!important}
.admin-table td,.admin-table th{padding:6px 8px!important;font-size:11px!important;overflow-wrap:break-word!important}
.chat-page textarea,.chat-page input{font-size:16px!important}
input,textarea,select{touch-action:manipulation}
}
.flyout-item:hover .flyout-tip{opacity:1!important}`
document.head.appendChild(_style)

// On press: replay the pop animation every time
document.addEventListener('mousedown', (e: MouseEvent) => {
  const target = (e.target as HTMLElement).closest('button,[data-slot="sidebar-menu-sub-button"]')
  if (target && !(target as HTMLButtonElement).disabled) {
    target.style.animation = 'none'
    void target.offsetWidth
    target.style.animation = 'btn-click 0.25s ease'
  }
}, true)

// Dialog inputs: move cursor to end, don't select all
document.addEventListener('focusin', (e: FocusEvent) => {
  const el = e.target as HTMLInputElement | HTMLTextAreaElement
  if ((el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') && el.value.length > 0 && el.closest('[role="dialog"]')) {
    setTimeout(() => el.setSelectionRange(el.value.length, el.value.length), 0)
  }
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ThemeProvider>
      <TooltipProvider>
        <App />
      </TooltipProvider>
    </ThemeProvider>
  </StrictMode>,
)
