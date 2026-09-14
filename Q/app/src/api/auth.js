import request from './request'

// 认证接口(契约见 docs/API.md 3.7)
export const authApi = {
  captcha: () => request.get('/auth/captcha'),
  register: (payload) => request.post('/auth/register', payload),
  login: (payload) => request.post('/auth/login', payload),
  logout: () => request.post('/auth/logout'),
  me: () => request.get('/auth/me'),
  resetRequest: (email) => request.post('/auth/reset/request', { email }),
  resetConfirm: (payload) => request.post('/auth/reset/confirm', payload),
}
