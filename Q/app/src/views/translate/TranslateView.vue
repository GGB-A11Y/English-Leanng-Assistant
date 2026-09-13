<script setup>
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { useTranslateStore } from '@/stores/translate'
import { useVocabularyStore } from '@/stores/vocabulary'
import { useBackendStore } from '@/stores/backend'
import BackendOffline from '@/components/common/BackendOffline.vue'
import { TRANSLATE_DIRECTIONS } from '@/constants'
import { formatDateTime } from '@/utils/format'

const store = useTranslateStore()
const vocabularyStore = useVocabularyStore()
const backendStore = useBackendStore()

const direction = ref('zh2en')
const text = ref('')
const translating = ref(false)
const result = ref(null)
const activeTab = ref('translation')
const addingWords = ref(new Set())

const explanation = computed(() => result.value?.explanation || {})

async function doTranslate() {
  const content = text.value.trim()
  if (!content || translating.value) return
  translating.value = true
  try {
    result.value = await store.translate({
      text: content,
      source_lang: direction.value === 'zh2en' ? 'zh' : 'en',
      target_lang: direction.value === 'zh2en' ? 'en' : 'zh',
    })
    activeTab.value = 'translation'
  } catch {
    // 错误已由 request.js 统一提示
  } finally {
    translating.value = false
  }
}

function viewHistory(record) {
  text.value = record.text
  direction.value = record.targetLang === 'en' ? 'zh2en' : 'en2zh'
  result.value = { translation: record.translation, explanation: record.explanation }
  activeTab.value = 'translation'
}

async function addToVocabulary(word) {
  if (addingWords.value.has(word)) return
  addingWords.value.add(word)
  try {
    await vocabularyStore.addWord(word)
    ElMessage.success(`已将「${word}」加入单词本`)
  } catch {} finally {
    addingWords.value.delete(word)
  }
}

async function copyTranslation() {
  try {
    await navigator.clipboard.writeText(result.value.translation)
    ElMessage.success('已复制译文')
  } catch {
    ElMessage.error('复制失败')
  }
}
</script>

<template>
  <div class="translate-view">
    <BackendOffline v-if="backendStore.online === false" style="margin-bottom: 16px" />

    <el-row :gutter="20">
      <el-col :xs="24" :lg="16">
        <el-card>
          <div class="input-head">
            <el-segmented v-model="direction" :options="TRANSLATE_DIRECTIONS" />
            <el-button
              type="primary"
              :loading="translating"
              :disabled="!text.trim() || backendStore.online === false"
              @click="doTranslate"
            >
              翻译并解析
            </el-button>
          </div>
          <el-input
            v-model="text"
            type="textarea"
            :rows="8"
            maxlength="2000"
            show-word-limit
            :placeholder="direction === 'zh2en' ? '输入中文,翻译成英文…' : '输入英文,翻译成中文…'"
          />
          <div v-if="translating" class="translating-hint">
            <el-icon class="is-loading"><Loading /></el-icon>
            AI 正在翻译与解析,约需 20 秒,请稍候…
          </div>

          <template v-if="result">
            <el-tabs v-model="activeTab" class="result-tabs">
              <el-tab-pane label="译文" name="translation">
                <div class="translation-box">
                  <div class="translation-text">{{ result.translation }}</div>
                  <el-button link type="primary" @click="copyTranslation">
                    <el-icon><CopyDocument /></el-icon>复制
                  </el-button>
                </div>
              </el-tab-pane>

              <el-tab-pane label="词组解析" name="phrases">
                <template v-if="explanation.phrases?.length">
                  <div v-for="(p, i) in explanation.phrases" :key="i" class="explain-item">
                    <div class="explain-title">{{ p.phrase }}</div>
                    <div class="explain-meaning">{{ p.meaning }}</div>
                    <div v-if="p.note" class="explain-note">{{ p.note }}</div>
                  </div>
                </template>
                <el-empty v-else description="无词组解析" :image-size="60" />
              </el-tab-pane>

              <el-tab-pane label="语法点" name="grammar">
                <template v-if="explanation.grammar_points?.length">
                  <div v-for="(g, i) in explanation.grammar_points" :key="i" class="explain-item">
                    <div class="explain-title">{{ g.point }}</div>
                    <div class="explain-meaning">{{ g.explanation }}</div>
                  </div>
                </template>
                <el-empty v-else description="无语法解析" :image-size="60" />
              </el-tab-pane>

              <el-tab-pane label="重点词汇" name="words">
                <template v-if="explanation.key_words?.length">
                  <div v-for="(w, i) in explanation.key_words" :key="i" class="explain-item word-item">
                    <div class="explain-title">
                      {{ w.word }}
                      <span v-if="w.phonetic" class="word-phonetic">/{{ w.phonetic }}/</span>
                    </div>
                    <div class="explain-meaning">{{ w.meaning }}</div>
                    <el-button
                      link
                      type="primary"
                      size="small"
                      :disabled="backendStore.online === false"
                      :loading="addingWords.has(w.word)"
                      @click="addToVocabulary(w.word)"
                    >
                      <el-icon><Plus /></el-icon>加入单词本
                    </el-button>
                  </div>
                </template>
                <el-empty v-else description="无重点词汇" :image-size="60" />
              </el-tab-pane>

              <el-tab-pane label="其他表达" name="alternatives">
                <ul v-if="explanation.alternatives?.length" class="alt-list">
                  <li v-for="(a, i) in explanation.alternatives" :key="i">{{ a }}</li>
                </ul>
                <el-empty v-else description="无其他表达" :image-size="60" />
              </el-tab-pane>
            </el-tabs>
          </template>
        </el-card>
      </el-col>

      <el-col :xs="24" :lg="8">
        <el-card class="history-card">
          <template #header>
            <div class="history-head">
              <span>翻译历史</span>
              <el-popconfirm v-if="store.history.length" title="清空全部历史?" @confirm="store.clear()">
                <template #reference>
                  <el-button link type="danger" size="small">清空</el-button>
                </template>
              </el-popconfirm>
            </div>
          </template>
          <el-scrollbar class="history-scroll">
            <div
              v-for="item in store.history"
              :key="item.id"
              class="history-item"
              @click="viewHistory(item)"
            >
              <div class="history-text">{{ item.text }}</div>
              <div class="history-meta">
                <span>{{ item.sourceLang === 'zh' ? '中→英' : '英→中' }}</span>
                <span>{{ formatDateTime(item.createdAt) }}</span>
                <el-button link type="danger" size="small" @click.stop="store.removeItem(item.id)">
                  <el-icon><Delete /></el-icon>
                </el-button>
              </div>
            </div>
            <el-empty v-if="!store.history.length" description="暂无翻译历史(本地保存,离线也可查看)" :image-size="70" />
          </el-scrollbar>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped>
.input-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
  flex-wrap: wrap;
  gap: 10px;
}
.translating-hint {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 10px;
  font-size: 13px;
  color: var(--el-color-primary);
}
.result-tabs {
  margin-top: 16px;
}
.translation-box {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  background: var(--el-fill-color-light);
  border-radius: 8px;
  padding: 16px;
}
.translation-text {
  flex: 1;
  font-size: 16px;
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-word;
}
.explain-item {
  border-left: 3px solid var(--el-color-primary-light-5);
  padding: 4px 0 12px 12px;
  margin-bottom: 8px;
}
.word-item {
  position: relative;
  padding-bottom: 8px;
}
.explain-title {
  font-weight: 600;
  font-size: 15px;
}
.word-phonetic {
  color: var(--el-text-color-secondary);
  font-weight: normal;
  font-size: 13px;
}
.explain-meaning {
  color: var(--el-text-color-regular);
  font-size: 14px;
  margin-top: 2px;
}
.explain-note {
  color: var(--el-text-color-secondary);
  font-size: 13px;
  margin-top: 2px;
}
.alt-list {
  padding-left: 1.4em;
  margin: 0;
  line-height: 1.9;
}
.history-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.history-item {
  padding: 10px;
  border-radius: 6px;
  cursor: pointer;
  margin-bottom: 6px;
}
.history-item:hover {
  background: var(--el-fill-color-light);
}
.history-text {
  font-size: 14px;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}
.history-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-top: 4px;
}

/* ---- 响应式适配 ---- */

/* 历史区高度:桌面固定 560px;矮屏/手机收缩
 * (el-scrollbar 的 height prop 是内联样式,media query 压不过,改 class 控制) */
.history-scroll {
  height: 560px;
  height: min(560px, 60dvh);
  min-height: 240px;
}

@media (max-width: 767px) {
  .translation-text {
    font-size: 14px;
  }
  .explain-title {
    font-size: 14px;
  }
  .input-head {
    gap: 10px;
  }
}
</style>
