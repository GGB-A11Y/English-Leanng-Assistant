// 格式化小工具(不引入 dayjs,用 Intl 实现)

const dateTimeFmt = new Intl.DateTimeFormat('zh-CN', {
  dateStyle: 'medium',
  timeStyle: 'short',
})

export function formatDateTime(iso) {
  if (!iso) return '—'
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return '—'
  return dateTimeFmt.format(date)
}

// 得分 → 颜色(Element Plus 状态色),ratio 为 0~1
export function scoreColor(ratio) {
  if (ratio >= 0.8) return '#67c23a'
  if (ratio >= 0.6) return '#e6a23c'
  return '#f56c6c'
}

// 本地记录 ID:crypto.randomUUID 仅在 secure context(localhost/HTTPS)可用,
// 局域网 IP 访问时不存在,降级为时间戳+随机串
export function genId() {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID()
  }
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`
}
