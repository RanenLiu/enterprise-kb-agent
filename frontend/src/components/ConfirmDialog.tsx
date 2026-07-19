import {
  Dialog,
  DialogContent,
  DialogFooter,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { AlertTriangle, Trash2 } from 'lucide-react'

interface ConfirmDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  title?: string
  description?: string
  confirmText?: string
  cancelText?: string
  variant?: 'destructive' | 'default'
  onConfirm: () => void
}

const iconMap = {
  destructive: Trash2,
  default: AlertTriangle,
}

export function ConfirmDialog({
  open,
  onOpenChange,
  title = '确认操作',
  description = '确定要执行此操作吗？',
  confirmText = '确认',
  cancelText = '取消',
  variant = 'destructive',
  onConfirm,
}: ConfirmDialogProps) {
  const Icon = iconMap[variant]

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      {/* @ts-ignore - role alertdialog for accessibility */}
      
      <DialogContent
        className="sm:max-w-sm p-0 gap-0 overflow-hidden shadow-2xl"
        showCloseButton={false}
        style={{ border: "1px solid var(--border)" }}
      >
        {/* Header: icon + title */}
        <div
          className={`flex items-center gap-3 px-5 pt-4 pb-3 ${
            variant === 'destructive'
              ? 'bg-destructive/5 border-b'
              : 'bg-amber-500/5 border-b'
          }`}
        >
          <div
            className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${
              variant === 'destructive'
                ? 'bg-destructive/10 text-destructive'
                : 'bg-amber-500/10 text-amber-600'
            }`}
          >
            <Icon className="h-4 w-4" aria-hidden="true" />
          </div>
          <h2 className="text-sm font-semibold">{title}</h2>
        </div>

        {/* Body: description */}
        <div className="px-5 py-4">
          <p className="text-sm text-muted-foreground leading-relaxed">
            {description}
          </p>
        </div>

        {/* Actions */}
        <DialogFooter className="flex-row gap-2 px-5 py-3 border-t sm:justify-end">
          <Button variant="outline" onClick={() => onOpenChange(false)} className="h-9 cursor-pointer">
            {cancelText}
          </Button>
          <Button
            variant={variant}
            onClick={() => { onConfirm(); onOpenChange(false) }}
            className="h-9 cursor-pointer"
          >
            {confirmText}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
