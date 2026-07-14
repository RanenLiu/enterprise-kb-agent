import { useState, useCallback } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { api } from '@/api/client'
import { toast } from 'sonner'

interface UploadDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess: () => void
}

export function UploadDialog({ open, onOpenChange, onSuccess }: UploadDialogProps) {
  const [files, setFiles] = useState<File[]>([])
  const [uploading, setUploading] = useState(false)

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    const dropped = Array.from(e.dataTransfer.files)
    setFiles(prev => [...prev, ...dropped])
  }, [])

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = Array.from(e.target.files || [])
    setFiles(prev => [...prev, ...selected])
  }, [])

  const handleUpload = async () => {
    if (files.length === 0) return
    setUploading(true)
    try {
      for (const file of files) {
        await api.uploadDocument(file)
      }
      toast.success(`${files.length} 个文件上传成功`)
      setFiles([])
      onSuccess()
      onOpenChange(false)
    } catch (err: any) {
      toast.error(err.message || '上传失败')
    } finally {
      setUploading(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>上传文档</DialogTitle>
        </DialogHeader>
        <div
          className="border-2 border-dashed rounded-lg p-8 text-center cursor-pointer hover:bg-muted/50"
          onDrop={handleDrop}
          onDragOver={e => e.preventDefault()}
          onClick={() => document.getElementById('file-input')?.click()}
        >
          <p className="text-muted-foreground mb-2">拖拽文件到此处，或点击选择</p>
          <p className="text-xs text-muted-foreground">
            支持 PDF/DOCX/XLSX/PPTX/MD/TXT/CSV/邮件，上限 50MB
          </p>
          <input
            id="file-input"
            type="file"
            multiple
            className="hidden"
            onChange={handleFileSelect}
          />
        </div>
        {files.length > 0 && (
          <div className="space-y-1">
            {files.map((f, i) => (
              <div key={i} className="text-sm flex justify-between py-1 border-b last:border-0">
                <span>{f.name}</span>
                <span className="text-muted-foreground">{(f.size / 1024 / 1024).toFixed(1)}MB</span>
              </div>
            ))}
          </div>
        )}
        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={() => onOpenChange(false)}>取消</Button>
          <Button onClick={handleUpload} disabled={files.length === 0 || uploading}>
            {uploading ? '上传中...' : '上传'}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
