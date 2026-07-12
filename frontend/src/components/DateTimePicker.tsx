import { useState, useRef, useEffect } from 'react'
import { ChevronLeft, ChevronRight, X } from 'lucide-react'

interface Props {
  value: string
  onChange: (v: string) => void
  placeholder?: string
}

const WEEK = ['日', '一', '二', '三', '四', '五', '六']
const MONTHS = ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月']

function pad(n: number) { return n.toString().padStart(2, '0') }

export function DateTimePicker({ value, onChange, placeholder = "时间" }: Props) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  // Calendar state
  const now = new Date()
  const [year, setYear] = useState(now.getFullYear())
  const [month, setMonth] = useState(now.getMonth())
  const [selDate, setSelDate] = useState<number | null>(now.getDate())
  const [selHour, setSelHour] = useState(now.getHours())
  const [selMin, setSelMin] = useState(now.getMinutes())

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  // Reset when opening
  useEffect(() => {
    if (open && value) {
      const d = new Date(value)
      if (!isNaN(d.getTime())) {
        setYear(d.getFullYear()); setMonth(d.getMonth())
        setSelDate(d.getDate()); setSelHour(d.getHours()); setSelMin(d.getMinutes())
        return
      }
    }
    if (open) {
      const d = new Date()
      setYear(d.getFullYear()); setMonth(d.getMonth())
      setSelDate(d.getDate()); setSelHour(d.getHours()); setSelMin(d.getMinutes())
    }
  }, [open])

  const displayValue = value ? value.replace('T', ' ') : ''

  const daysInMonth = new Date(year, month + 1, 0).getDate()
  const firstDay = new Date(year, month, 1).getDay()

  const days: (number | null)[] = []
  for (let i = 0; i < firstDay; i++) days.push(null)
  for (let i = 1; i <= daysInMonth; i++) days.push(i)

  const confirm = () => {
    if (selDate) {
      const d = `${year}-${pad(month + 1)}-${pad(selDate)}T${pad(selHour)}:${pad(selMin)}`
      onChange(d)
      setOpen(false)
    }
  }

  const today = () => {
    const d = new Date()
    setYear(d.getFullYear()); setMonth(d.getMonth())
    setSelDate(d.getDate()); setSelHour(d.getHours()); setSelMin(d.getMinutes())
    const v = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
    onChange(v)
    setOpen(false)
  }

  const quickOptions = [
    { label: '今天', fn: today },
    { label: '昨天', fn: () => {
      const d = new Date(); d.setDate(d.getDate() - 1)
      setYear(d.getFullYear()); setMonth(d.getMonth()); setSelDate(d.getDate())
      setSelHour(d.getHours()); setSelMin(d.getMinutes())
      onChange(`${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`)
      setOpen(false)
    }},
    { label: '本月', fn: () => {
      const d = new Date(); d.setDate(1)
      setYear(d.getFullYear()); setMonth(d.getMonth()); setSelDate(1)
      setSelHour(0); setSelMin(0)
      onChange(`${d.getFullYear()}-${pad(d.getMonth() + 1)}-01T00:00`)
      setOpen(false)
    }},
    { label: '上月', fn: () => {
      const d = new Date(); d.setMonth(d.getMonth() - 1); d.setDate(1)
      setYear(d.getFullYear()); setMonth(d.getMonth()); setSelDate(1)
      setSelHour(0); setSelMin(0)
      onChange(`${d.getFullYear()}-${pad(d.getMonth() + 1)}-01T00:00`)
      setOpen(false)
    }},
  ]

  return (
    <div className="relative" ref={ref}>
      <input
        type="text"
        readOnly
        placeholder={placeholder}
        className="h-8 w-[140px] text-xs px-2 rounded-md border border-input bg-background cursor-pointer"
        value={displayValue}
        onClick={() => setOpen(!open)}
      />
      {open && (
        <div className="absolute top-full mt-1 left-0 z-50 w-[260px] rounded-lg border bg-popover p-3 shadow-lg">
          {/* Header */}
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium">选择日期时间</span>
            <button type="button" className="h-5 w-5 flex items-center justify-center rounded hover:bg-muted cursor-pointer" onClick={() => setOpen(false)}>
              <X className="h-3.5 w-3.5" />
            </button>
          </div>

          {/* Quick options */}
          <div className="flex gap-1 mb-2">
            {quickOptions.map((opt) => (
              <button key={opt.label} type="button" className="flex-1 px-1 py-1 text-xs rounded hover:bg-muted cursor-pointer text-center"
                onClick={opt.fn}>{opt.label}</button>
            ))}
          </div>

          <div className="border-t mb-2" />

          {/* Month navigation */}
          <div className="flex items-center justify-between mb-1">
            <button type="button" className="h-6 w-6 flex items-center justify-center rounded hover:bg-muted cursor-pointer"
              onClick={() => { if (month === 0) { setYear(y => y - 1); setMonth(11) } else setMonth(m => m - 1) }}>
              <ChevronLeft className="h-3.5 w-3.5" />
            </button>
            <span className="text-xs font-medium">{year}年{MONTHS[month]}</span>
            <button type="button" className="h-6 w-6 flex items-center justify-center rounded hover:bg-muted cursor-pointer"
              onClick={() => { if (month === 11) { setYear(y => y + 1); setMonth(0) } else setMonth(m => m + 1) }}>
              <ChevronRight className="h-3.5 w-3.5" />
            </button>
          </div>

          {/* Weekday headers */}
          <div className="grid grid-cols-7 mb-1">
            {WEEK.map((w) => (
              <div key={w} className="h-6 flex items-center justify-center text-xs text-muted-foreground">{w}</div>
            ))}
          </div>

          {/* Calendar grid */}
          <div className="grid grid-cols-7">
            {days.map((d, i) => (
              <button
                key={i}
                type="button"
                disabled={d === null}
                className={`h-7 text-xs rounded cursor-pointer
                  ${d === null ? 'invisible' : 'hover:bg-muted'}
                  ${d === selDate ? 'bg-primary text-primary-foreground hover:bg-primary' : ''}`}
                onClick={() => setSelDate(d!)}
              >
                {d}
              </button>
            ))}
          </div>

          {/* Time select */}
          <div className="flex items-center justify-center gap-2 mt-2 pt-2 border-t">
            <span className="text-xs text-muted-foreground">时间</span>
            <select className="h-7 text-xs px-1 rounded border border-input bg-background" value={selHour}
              onChange={(e) => setSelHour(parseInt(e.target.value))}>
              {Array.from({ length: 24 }, (_, i) => (
                <option key={i} value={i}>{pad(i)}</option>
              ))}
            </select>
            <span className="text-xs">:</span>
            <select className="h-7 text-xs px-1 rounded border border-input bg-background" value={selMin}
              onChange={(e) => setSelMin(parseInt(e.target.value))}>
              {Array.from({ length: 60 }, (_, i) => (
                <option key={i} value={i}>{pad(i)}</option>
              ))}
            </select>
          </div>

          {/* Action buttons */}
          <div className="flex gap-1 mt-2">
            <button type="button" className="flex-1 px-2 py-1.5 text-xs rounded bg-primary text-primary-foreground hover:bg-primary/90 cursor-pointer"
              onClick={confirm}>确定</button>
            <button type="button" className="flex-1 px-2 py-1.5 text-xs rounded hover:bg-muted cursor-pointer"
              onClick={() => { onChange(''); setOpen(false) }}>清除</button>
          </div>
        </div>
      )}
    </div>
  )
}
