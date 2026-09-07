import { defineStore } from 'pinia'
import { ElMessage } from 'element-plus'
import { chatApi } from '@/api/chat'
import { streamSSE } from '@/api/sse'

// AI 对话:会话列表 + 当前会话消息 + 流式生成状态
let selectSeq = 0 // 会话切换请求序号,用于丢弃乱序响应

export const useChatStore = defineStore('chat', {
  state: () => ({
    sessions: [],
    currentSessionId: null,
    messages: [],
    sending: false,
    streaming: false,
    streamingContent: '',
    abortController: null,
  }),
  actions: {
    async fetchSessions() {
      this.sessions = await chatApi.listSessions()
    },
    async createSession() {
      if (this.streaming) return null // 生成中禁止新建,避免在途流错乱
      const session = await chatApi.createSession()
      this.sessions.unshift(session)
      this.currentSessionId = session.id
      this.messages = []
      return session
    },
    async selectSession(id) {
      if (this.streaming || id === this.currentSessionId) return
      const seq = ++selectSeq
      this.currentSessionId = id
      this.messages = []
      try {
        const data = await chatApi.getSession(id)
        if (seq !== selectSeq) return // 快速切换会话时响应乱序,丢弃旧结果
        this.messages = data.messages || []
      } catch {
        // 错误已由 request.js 提示
      }
    },
    async deleteSession(id) {
      if (this.streaming) return // 生成中禁止删除,避免在途流错乱
      await chatApi.deleteSession(id)
      this.sessions = this.sessions.filter((s) => s.id !== id)
      if (this.currentSessionId === id) {
        this.currentSessionId = null
        this.messages = []
      }
      ElMessage.success('对话已删除')
    },
    // 返回 true 表示消息已被接受(已推入列表),false 表示被拒绝(调用方应保留输入)
    async sendMessage(content) {
      content = content.trim()
      if (!content || this.sending || this.streaming) return false
      if (!this.currentSessionId) {
        try {
          await this.createSession()
        } catch {
          return false // 创建失败(如后端离线)时错误已提示
        }
      }

      this.messages.push({
        id: `local-u-${Date.now()}`,
        role: 'user',
        content,
        created_at: new Date().toISOString(),
      })
      const assistantDraft = {
        id: `local-a-${Date.now()}`,
        role: 'assistant',
        content: '',
        created_at: new Date().toISOString(),
        streaming: true,
        interrupted: false,
        error: false,
      }
      this.messages.push(assistantDraft)

      this.sending = true
      this.streaming = true
      this.streamingContent = ''
      this.abortController = new AbortController()

      try {
        await streamSSE(
          `/api/chat/sessions/${this.currentSessionId}/messages`,
          { content },
          {
            onDelta: (text) => {
              this.streamingContent += text
            },
            signal: this.abortController.signal,
          },
        )
        assistantDraft.content = this.streamingContent
        assistantDraft.streaming = false
        this.fetchSessions().catch(() => {}) // 静默刷新会话消息数
      } catch (error) {
        assistantDraft.streaming = false
        assistantDraft.content = this.streamingContent
        if (error.name === 'AbortError') {
          assistantDraft.interrupted = true // 用户主动停止,保留部分内容
        } else {
          assistantDraft.error = true
          if (!assistantDraft.content) {
            // 完全没有产出:移除空气泡,由错误提示兜底
            const idx = this.messages.indexOf(assistantDraft)
            if (idx !== -1) this.messages.splice(idx, 1)
          }
          if (error.name === 'TypeError' || error.message === 'Failed to fetch') {
            ElMessage.error('无法连接后端服务,请确认后端已启动(端口 8000)')
          } else {
            ElMessage.error(error.message || 'AI 生成失败,请重试')
          }
        }
      } finally {
        this.sending = false
        this.streaming = false
        this.streamingContent = ''
        this.abortController = null
      }
      return true
    },
    stopStreaming() {
      this.abortController?.abort()
    },
  },
  // 仅记住上次打开的会话
  persist: { key: 'chat', pick: ['currentSessionId'] },
})
