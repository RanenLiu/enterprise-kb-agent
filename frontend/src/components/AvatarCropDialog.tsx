import { useState } from 'react'
import Cropper from 'react-easy-crop'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Slider } from '@/components/ui/slider'
import { toast } from 'sonner'
import { api } from '@/api/client'
import { ZoomIn, ZoomOut } from 'lucide-react'

interface Props {
  open: boolean
  onOpenChange: (open: boolean) => void
  file: File | null
  onComplete: (url: string) => void
}

type Area = { width: number; height: number; x: number; y: number }

export function AvatarCropDialog({ open, onOpenChange, file, onComplete }: Props) {
  const [crop, setCrop] = useState({ x: 0, y: 0 })
  const [zoom, setZoom] = useState(1)
  const [croppedAreaPixels, setCroppedAreaPixels] = useState<Area | null>(null)
  const [uploading, setUploading] = useState(false)

  const onCropComplete = (_: Area, croppedAreaPixels: Area) => {
    setCroppedAreaPixels(croppedAreaPixels)
  }

  const createCroppedImage = async (imageSrc: string, pixelCrop: Area): Promise<Blob> => {
    const image = await createImage(imageSrc)
    const canvas = document.createElement('canvas')
    canvas.width = pixelCrop.width
    canvas.height = pixelCrop.height
    const ctx = canvas.getContext('2d')!
    ctx.drawImage(
      image,
      pixelCrop.x, pixelCrop.y, pixelCrop.width, pixelCrop.height,
      0, 0, pixelCrop.width, pixelCrop.height,
    )
    return new Promise((resolve) => {
      canvas.toBlob((blob) => resolve(blob!), 'image/jpeg', 0.9)
    })
  }

  const createImage = (url: string): Promise<HTMLImageElement> =>
    new Promise((resolve, reject) => {
      const img = new Image()
      img.addEventListener('load', () => resolve(img))
      img.addEventListener('error', (e) => reject(e))
      img.src = url
    })

  const handleConfirm = async () => {
    if (!file || !croppedAreaPixels) return
    setUploading(true)
    try {
      const src = URL.createObjectURL(file)
      const croppedBlob = await createCroppedImage(src, croppedAreaPixels)
      URL.revokeObjectURL(src)
      const croppedFile = new File([croppedBlob], file.name, { type: 'image/jpeg' })
      const res = await api.uploadFile(croppedFile)
      onComplete(res.data.url)
      onOpenChange(false)
      toast.success('头像已更新')
    } catch (err: any) {
      toast.error(err.message || '裁剪失败')
    } finally {
      setUploading(false)
    }
  }

  const imageSrc = file ? URL.createObjectURL(file) : ''

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="text-lg">裁剪头像</DialogTitle>
        </DialogHeader>
        <div className="relative w-full h-64 bg-black/5 rounded-lg overflow-hidden">
          {imageSrc && (
            <Cropper
              image={imageSrc}
              crop={crop}
              zoom={zoom}
              aspect={1}
              cropShape="round"
              onCropChange={setCrop}
              onZoomChange={setZoom}
              onCropComplete={onCropComplete}
            />
          )}
        </div>
        <div className="flex items-center gap-3 px-1">
          <button type="button" onClick={() => setZoom((z) => Math.max(1, z - 0.2))} className="text-muted-foreground hover:text-foreground transition-colors">
            <ZoomOut className="h-4 w-4" />
          </button>
          <Slider
            value={[zoom]}
            min={1}
            max={3}
            step={0.1}
            onValueChange={([v]) => setZoom(v)}
            className="flex-1"
          />
          <button type="button" onClick={() => setZoom((z) => Math.min(3, z + 0.2))} className="text-muted-foreground hover:text-foreground transition-colors">
            <ZoomIn className="h-4 w-4" />
          </button>
        </div>
        <Button onClick={handleConfirm} disabled={uploading} className="w-full shadow-sm">
          {uploading ? '上传中...' : '确认裁剪'}
        </Button>
      </DialogContent>
    </Dialog>
  )
}
