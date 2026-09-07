import { defineStore } from 'pinia'
import { writingApi } from '@/api/writing'
import { genId } from '@/utils/format'

const RECORD_LIMIT = 50

// 作文草稿与批改记录由前端本地持久化(后端不存,见 docs/API.md)
export const useWritingStore = defineStore('writing', {
  state: () => ({
    draft: { title: '', content: '', requirement: '', topicId: '', topicTitle: '' },
    records: [], // { id, topic, topicTitle, title, content, requirement, result, createdAt }
  }),
  actions: {
    saveDraft(draft) {
      this.draft = { ...this.draft, ...draft }
    },
    async grade(payload, meta = {}) {
      const result = await writingApi.gradeEssay(payload)
      this.records.unshift({
        id: genId(),
        topic: payload.topic_id || '',
        topicTitle: meta.topicTitle || '',
        stage: meta.stage || '',
        title: payload.title || '',
        content: payload.content,
        requirement: payload.requirement || '',
        result,
        createdAt: new Date().toISOString(),
      })
      if (this.records.length > RECORD_LIMIT) {
        this.records = this.records.slice(0, RECORD_LIMIT)
      }
      return result
    },
    removeRecord(id) {
      this.records = this.records.filter((r) => r.id !== id)
    },
  },
  persist: { key: 'writing', pick: ['records', 'draft'] },
})
