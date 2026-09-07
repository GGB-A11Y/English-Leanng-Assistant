import { requestLong } from './request'

// 阅读理解接口(生成类,耗时较长)
export const readingApi = {
  generateArticle: (payload) => requestLong.post('/reading/articles/generate', payload),
  submitAnswers: (articleId, answers) =>
    requestLong.post(`/reading/articles/${articleId}/submit`, { answers }),
}
