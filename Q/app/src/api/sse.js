/**
 * 基于 fetch + ReadableStream 的 SSE 客户端(对话模块专用)。
 * 对话接口需要 POST 请求体,原生 EventSource 仅支持 GET,故用 fetch 实现。
 *
 * 帧格式约定(见 docs/API.md,每帧以 \n\n 分隔):
 *   data: {"type":"delta","content":"..."}   增量文本
 *   data: {"type":"done","message_id":"..."}  生成完成
 *   data: {"type":"error","message":"..."}    生成失败
 *   : ping                                    心跳注释行(忽略)
 *
 * @param {string} url  完整请求路径(含 /api 前缀)
 * @param {object} body 请求体 JSON
 * @param {object} handlers
 * @param {(text:string)=>void} handlers.onDelta 收到增量文本
 * @param {(msg:object)=>void} handlers.onDone  收到 done 帧
 * @param {AbortSignal} [handlers.signal]      用于"停止生成"的中止信号
 * @throws {Error} 网络失败(TypeError: Failed to fetch)、HTTP 非 2xx、error 帧、流意外中断
 */
export async function streamSSE(url, body, { onDelta, onDone, signal } = {}) {
  const res = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
    },
    body: JSON.stringify(body),
    signal,
  })

  if (!res.ok || !res.headers.get('content-type')?.includes('text/event-stream')) {
    const data = await res.json().catch(() => ({}))
    throw new Error(data.detail || `请求失败(${res.status})`)
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let finished = false

  const handleFrame = (frame) => {
    for (const line of frame.split('\n')) {
      if (!line.startsWith('data:')) continue // 心跳注释行等直接忽略
      const payload = line.slice(5).trim()
      if (!payload) continue
      let msg
      try {
        msg = JSON.parse(payload)
      } catch {
        continue // 解析失败的帧跳过,不中断流
      }
      if (msg.type === 'delta') {
        onDelta?.(msg.content ?? '')
      } else if (msg.type === 'done') {
        finished = true
        onDone?.(msg)
      } else if (msg.type === 'error') {
        throw new Error(msg.message || '生成失败')
      }
    }
  }

  // 帧分隔符同时兼容 \n\n 与 \r\n\r\n。
  // 不做全局 \r\n 归一化:分隔符若恰被分割在两个 chunk 之间,
  // 归一化会漏掉,直接在拼接后的 buffer 上匹配两种模式则天然安全。
  const FRAME_SEP = /\n\n|\r\n\r\n/
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    let match
    while ((match = FRAME_SEP.exec(buffer)) !== null) {
      const frame = buffer.slice(0, match.index)
      buffer = buffer.slice(match.index + match[0].length)
      handleFrame(frame)
    }
  }

  if (buffer.trim()) handleFrame(buffer)

  // 流结束但未收到 done 帧:后端异常中断,视为失败
  if (!finished) {
    throw new Error('连接中断,生成未完成')
  }
}
