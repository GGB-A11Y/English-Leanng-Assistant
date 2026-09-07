import request from './request'

// AI 对话会话接口(流式消息发送见 stores/chat.js 中的 streamSSE 调用)
export const chatApi = {
  listSessions: () => request.get('/chat/sessions'),
  createSession: () => request.post('/chat/sessions'),
  getSession: (id) => request.get(`/chat/sessions/${id}`),
  deleteSession: (id) => request.delete(`/chat/sessions/${id}`),
}
