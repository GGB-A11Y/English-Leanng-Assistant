import { defineStore } from 'pinia'
import axios from 'axios'

// 后端连接状态。用裸 axios 探测 /api/health,不经过 request.js(避免失败时弹错误提示)
const POLL_INTERVAL = 15000
let timer = null

export const useBackendStore = defineStore('backend', {
  state: () => ({
    online: null, // null = 检测中, true = 在线, false = 离线
    lastCheckedAt: null,
  }),
  actions: {
    async checkHealth() {
      try {
        await axios.get('/api/health', { timeout: 10000 })
        this.online = true
      } catch {
        this.online = false
      }
      this.lastCheckedAt = new Date().toISOString()
      return this.online
    },
    startPolling() {
      if (timer) return
      this.checkHealth()
      timer = setInterval(() => this.checkHealth(), POLL_INTERVAL)
    },
    stopPolling() {
      clearInterval(timer)
      timer = null
    },
  },
})
