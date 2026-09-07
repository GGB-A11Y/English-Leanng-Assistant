import request, { requestLong } from './request'

// 作文学习接口
export const writingApi = {
  fetchTopics: (stage, group) =>
    request.get('/writing/topics', {
      params: {
        stage: stage || undefined,
        group: group || undefined,
      },
    }),
  gradeEssay: (payload) => requestLong.post('/writing/essays/grade', payload),
  generateSample: (topicId) => requestLong.post('/writing/essays/sample', { topic_id: topicId }),
  addTopic: (payload) => request.post('/writing/topics', payload),
  parseTopics: (text) => requestLong.post('/writing/topics/parse', { text }),
  importTopics: (topics) => request.post('/writing/topics/import', { topics }),
  deleteTopic: (topicId) => request.delete(`/writing/topics/${topicId}`),
  updateTopic: (topicId, payload) => request.patch(`/writing/topics/${topicId}`, payload),
  fetchTopicGroups: () => request.get('/writing/groups'),
  createTopicGroup: (name) => request.post('/writing/groups', { name }),
  deleteTopicGroup: (name) => request.delete(`/writing/groups/${encodeURIComponent(name)}`),
}
