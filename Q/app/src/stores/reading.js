import { defineStore } from 'pinia'
import { readingApi } from '@/api/reading'
import { genId } from '@/utils/format'

const RECORD_LIMIT = 50

// 阅读理解:进行中的文章保存在内存,完成记录由前端本地持久化(含自定义分组)
export const useReadingStore = defineStore('reading', {
  state: () => ({
    current: null, // { article, answers: {question_id: answer}, submitted, result }
    records: [], // { id, article, answers, result, createdAt, groups: [] }
    recordGroups: [], // 自定义分组名列表(含空分组,与记录一起本地持久化)
  }),
  actions: {
    async generate(stage, topic) {
      const article = await readingApi.generateArticle({ stage, topic: topic || undefined })
      this.current = { article, answers: {}, submitted: false, result: null }
      return article
    },
    answer(questionId, value) {
      if (this.current && !this.current.submitted) {
        this.current.answers[questionId] = value
      }
    },
    async submit() {
      const answers = Object.entries(this.current.answers).map(([question_id, answer]) => ({
        question_id,
        answer,
      }))
      const result = await readingApi.submitAnswers(this.current.article.article_id, answers)
      this.current.result = result
      this.current.submitted = true
      this.records.unshift({
        id: genId(),
        article: this.current.article,
        answers: { ...this.current.answers },
        result,
        groups: [],
        createdAt: new Date().toISOString(),
      })
      if (this.records.length > RECORD_LIMIT) {
        this.records = this.records.slice(0, RECORD_LIMIT)
      }
      return result
    },
    reset() {
      this.current = null
    },
    removeRecord(id) {
      this.records = this.records.filter((r) => r.id !== id)
    },
    // ---- 自定义分组(记录本地保存,分组同样本地持久化) ----
    addRecordGroup(name) {
      if (!this.recordGroups.includes(name)) {
        this.recordGroups.push(name)
      }
      return name
    },
    removeRecordGroup(name) {
      this.recordGroups = this.recordGroups.filter((g) => g !== name)
      this.records = this.records.map((r) => ({
        ...r,
        groups: (r.groups || []).filter((g) => g !== name),
      }))
    },
    setRecordGroups(id, groups) {
      const record = this.records.find((r) => r.id === id)
      if (record) {
        record.groups = [...groups]
      }
    },
  },
  persist: { key: 'reading', pick: ['records', 'recordGroups'] },
})
