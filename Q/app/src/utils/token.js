// 登录态的唯一真相源(localStorage key: auth,JSON { token, user })。
// request.js / sse.js / router 守卫 / auth store 共用,
// 避免在 axios 拦截器里 import pinia store(模块时序与循环依赖风险)。
const KEY = 'auth'

export function getStoredAuth() {
  try {
    const data = JSON.parse(localStorage.getItem(KEY))
    return data && typeof data === 'object' ? data : {}
  } catch {
    return {}
  }
}

export function getToken() {
  return getStoredAuth().token || ''
}

export function setAuth({ token, user }) {
  localStorage.setItem(KEY, JSON.stringify({ token, user }))
}

export function clearAuth() {
  localStorage.removeItem(KEY)
}
