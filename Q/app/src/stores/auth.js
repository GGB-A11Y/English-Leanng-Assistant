import { defineStore } from 'pinia'
import { authApi } from '@/api/auth'
import { getStoredAuth, setAuth, clearAuth } from '@/utils/token'

// 登录态:内存态由 token.js(localStorage)恢复,持久化统一走 token.js
// (不用 persistedstate 插件,避免双写与初始化时序问题)
export const useAuthStore = defineStore('auth', {
  state: () => {
    const stored = getStoredAuth()
    return {
      token: stored.token || '',
      user: stored.user || null,
    }
  },
  getters: {
    isLoggedIn: (s) => Boolean(s.token),
  },
  actions: {
    _apply({ token, user }) {
      this.token = token
      this.user = user
      setAuth({ token, user })
    },
    async login(payload) {
      const data = await authApi.login(payload)
      this._apply(data)
      return data
    },
    async register(payload) {
      const data = await authApi.register(payload)
      this._apply(data)
      return data
    },
    async fetchMe() {
      const user = await authApi.me()
      this.user = user
      setAuth({ token: this.token, user })
      return user
    },
    async logout() {
      try {
        await authApi.logout()
      } catch {
        // 后端失败也照常清理本地登录态
      }
      clearAuth()
      this.token = ''
      this.user = null
    },
    clearLocal() {
      clearAuth()
      this.token = ''
      this.user = null
    },
  },
})
