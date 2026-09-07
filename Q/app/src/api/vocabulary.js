import request, { requestLong } from './request'

// 单词本 / 复习(SM-2)/ 自测 / 内置词库接口
export const vocabularyApi = {
  fetchWords: (params) => request.get('/vocabulary/words', { params }),
  fetchBuiltin: () => request.get('/vocabulary/builtin'),
  importStage: (stage) => request.post('/vocabulary/words/import', { stage }),
  deleteStage: (stage) => request.delete(`/vocabulary/builtin/${stage}`),
  fetchGroups: () => request.get('/vocabulary/groups'),
  createGroup: (name) => request.post('/vocabulary/groups', { name }),
  deleteGroup: (name) => request.delete(`/vocabulary/groups/${encodeURIComponent(name)}`),
  addWord: (word) => requestLong.post('/vocabulary/words', { word }),
  getWord: (id) => request.get(`/vocabulary/words/${id}`),
  regenerateWord: (id) => requestLong.post(`/vocabulary/words/${id}/generate`),
  updateWord: (id, patch) => request.patch(`/vocabulary/words/${id}`, patch),
  deleteWord: (id) => request.delete(`/vocabulary/words/${id}`),
  fetchDue: (params) => request.get('/vocabulary/review/due', { params }),
  submitReview: (wordId, quality) => request.post(`/vocabulary/review/${wordId}`, { quality }),
  startQuiz: (count) => request.get('/vocabulary/quiz', { params: { count } }),
  submitQuiz: (quizId, answers) => request.post(`/vocabulary/quiz/${quizId}/submit`, { answers }),
}
