import { requestLong } from './request'

// 翻译接口(生成类,耗时较长)
export const translateApi = {
  translate: (payload) => requestLong.post('/translate', payload),
}
