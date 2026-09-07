import { defineStore } from 'pinia'
import { vocabularyApi } from '@/api/vocabulary'

// 单词本(以后端数据为准,不持久化)
export const useVocabularyStore = defineStore('vocabulary', {
  state: () => ({
    // 单词列表(分页 + 搜索 + 分组/学习状态筛选)
    words: [],
    total: 0,
    page: 1,
    pageSize: 10,
    query: '',
    group: '',
    status: '',
    loading: false,
    // 背诵模式(到期复习队列)
    dueWords: [],
    dueCount: 0,
    // 自测
    quiz: null, // { quiz_id, questions, results }
    // 浏览过的单词标签累积(供详情页标签联想,不受分页限制)
    knownTags: [],
  }),
  actions: {
    _mergeTags(entries) {
      const seen = new Set(this.knownTags)
      for (const w of entries) {
        for (const t of w.tags || []) seen.add(t)
      }
      this.knownTags = [...seen]
    },
    async fetchWords() {
      this.loading = true
      try {
        const data = await vocabularyApi.fetchWords({
          page: this.page,
          page_size: this.pageSize,
          q: this.query || undefined,
          group: this.group || undefined,
          status: this.status || undefined,
        })
        this.words = data.items
        this.total = data.total
        this._mergeTags(data.items)
      } finally {
        this.loading = false
      }
    },
    async addWord(word) {
      const entry = await vocabularyApi.addWord(word)
      this._mergeTags([entry])
      // 无任何筛选条件且在第一页时才就地插入;否则刷新列表(避免新词混进不符合筛选条件的视图)
      if (this.page === 1 && !this.query && !this.group && !this.status) {
        this.words.unshift(entry)
        this.total += 1
      } else {
        await this.fetchWords()
      }
      return entry
    },
    async getWord(id) {
      const entry = await vocabularyApi.getWord(id)
      const idx = this.words.findIndex((w) => String(w.id) === String(id))
      if (idx !== -1) this.words[idx] = entry
      return entry
    },
    async regenerateWord(id) {
      const entry = await vocabularyApi.regenerateWord(id)
      const idx = this.words.findIndex((w) => String(w.id) === String(id))
      if (idx !== -1) this.words[idx] = entry
      this._mergeTags([entry])
      return entry
    },
    async updateWord(id, patch) {
      const entry = await vocabularyApi.updateWord(id, patch)
      const idx = this.words.findIndex((w) => String(w.id) === String(id))
      if (idx !== -1) this.words[idx] = entry
      this._mergeTags([entry])
      return entry
    },
    async deleteWord(id) {
      await vocabularyApi.deleteWord(id)
      this.words = this.words.filter((w) => String(w.id) !== String(id))
      this.total = Math.max(0, this.total - 1)
      // 删空当前页且不在第一页:回退一页,避免停留在空页
      if (this.words.length === 0 && this.page > 1) {
        this.page -= 1
        await this.fetchWords().catch(() => {})
      }
    },
    async fetchDue(includeNew = true, limit = 20) {
      const data = await vocabularyApi.fetchDue({ include_new: includeNew, limit })
      this.dueWords = data.items
      this.dueCount = data.due_count
      return data
    },
    async submitReview(wordId, quality) {
      const result = await vocabularyApi.submitReview(wordId, quality)
      const idx = this.words.findIndex((w) => String(w.id) === String(wordId))
      if (idx !== -1) this.words[idx] = { ...this.words[idx], ...result }
      return result
    },
    async startQuiz(count = 10) {
      const data = await vocabularyApi.startQuiz(count)
      this.quiz = { ...data, results: null }
      return this.quiz
    },
    async submitQuiz(answers) {
      const data = await vocabularyApi.submitQuiz(this.quiz.quiz_id, answers)
      this.quiz.results = data
      return data
    },
    resetQuiz() {
      this.quiz = null
    },
  },
})
