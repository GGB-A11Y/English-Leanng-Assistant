import axios from 'axios'
import { ElMessage } from 'element-plus'

// 统一 axios 封装。开发环境经 Vite proxy 转发到后端 http://127.0.0.1:8000
// 契约见 docs/API.md:错误体统一为 {"detail": "..."}(FastAPI 默认)

const request = axios.create({
  baseURL: '/api',
  timeout: 15000,
})

// 生成类接口(翻译/批改/生成文章/生成词条)耗时可达 10~60s,单独用更长超时
export const requestLong = axios.create({
  baseURL: '/api',
  timeout: 120000,
})

// 归一化 FastAPI 错误信息:detail 可能是字符串或 422 校验错误数组
function normalizeDetail(data) {
  const detail = data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) return detail.map((item) => item.msg).join('; ')
  return ''
}

function setup(instance) {
  instance.interceptors.response.use(
    // 后端返回裸业务 JSON,直接返回 data
    (res) => res.data,
    (error) => {
      const { response } = error
      if (response) {
        const message = normalizeDetail(response.data) || `请求失败(${response.status})`
        ElMessage.error(message)
      } else {
        // 网络错误 / 后端未启动 / 超时:全局提示,页面层由 BackendOffline 组件兜底
        ElMessage.error('无法连接后端服务,请确认后端已启动(端口 8000)')
      }
      return Promise.reject(error)
    },
  )
}

setup(request)
setup(requestLong)

// 如有鉴权需求,可在此添加请求拦截器(扩展点)

export default request
