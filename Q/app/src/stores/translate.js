import { defineStore } from 'pinia'
import { translateApi } from '@/api/translate'
import { genId } from '@/utils/format'

const HISTORY_LIMIT = 100

// 翻译历史由前端本地持久化(后端不存,见 docs/API.md 存储职责划分)
export const useTranslateStore = defineStore('translate', {
  state: () => ({
    history: [], // { id, text, sourceLang, targetLang, translation, explanation, createdAt }
  }),
  actions: {
    async translate(payload) {
      const data = await translateApi.translate(payload)
      this.addRecord({
        id: genId(),
        text: payload.text,
        sourceLang: payload.source_lang,
        targetLang: payload.target_lang,
        translation: data.translation,
        explanation: data.explanation,
        createdAt: new Date().toISOString(),
      })
      return data
    },
    addRecord(record) {
      this.history.unshift(record)
      if (this.history.length > HISTORY_LIMIT) {
        this.history = this.history.slice(0, HISTORY_LIMIT)
      }
    },
    removeItem(id) {
      this.history = this.history.filter((item) => item.id !== id)
    },
    clear() {
      this.history = []
    },
  },
  persist: { key: 'translate-history', pick: ['history'] },
})
