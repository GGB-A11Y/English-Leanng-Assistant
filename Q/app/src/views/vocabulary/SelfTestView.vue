<script setup>
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { useVocabularyStore } from '@/stores/vocabulary'
import { useBackendStore } from '@/stores/backend'
import { vocabularyApi } from '@/api/vocabulary'
import BackendOffline from '@/components/common/BackendOffline.vue'
import { useIsXs } from '@/composables/useMediaQuery'
import { scoreColor } from '@/utils/format'

const store = useVocabularyStore()
const backendStore = useBackendStore()

// 窄屏:错题表卡片化
const isXs = useIsXs()

const step = ref('setup') // setup | answering | result
const count = ref(10)
const loading = ref(false)
const currentIndex = ref(0)
const answers = ref([]) // { word, answer_index }
const addingWords = ref(new Set())

const quiz = computed(() => store.quiz)
const questions = computed(() => quiz.value?.questions || [])
const currentQuestion = computed(() => questions.value[currentIndex.value] || null)
const results = computed(() => quiz.value?.results || null)
const scorePercent = computed(() =>
  results.value ? Math.round((results.value.score / results.value.total) * 100) : 0,
)
const wrongResults = computed(() =>
  (results.value?.results || []).filter((r) => !r.correct),
)

async function start() {
  if (loading.value) return
  loading.value = true
  try {
    await store.startQuiz(count.value)
    answers.value = questions.value.map((q) => ({ word: q.word, answer_index: null }))
    currentIndex.value = 0
    step.value = 'answering'
  } catch {
    // 错误已提示
  } finally {
    loading.value = false
  }
}

function next() {
  if (currentIndex.value < questions.value.length - 1) currentIndex.value += 1
}

function prev() {
  if (currentIndex.value > 0) currentIndex.value -= 1
}

const isLast = computed(() => currentIndex.value === questions.value.length - 1)
const allAnswered = computed(() => answers.value.every((a) => a.answer_index !== null))

async function submit() {
  if (loading.value || !allAnswered.value) return
  loading.value = true
  try {
    await store.submitQuiz(answers.value)
    step.value = 'result'
  } catch {
    // 错误已提示
  } finally {
    loading.value = false
  }
}

async function markHard(word) {
  if (addingWords.value.has(word)) return
  addingWords.value.add(word)
  try {
    // 自测题出自单词本,错词必然已存在(直接 addWord 会 409):
    // 改为打「易错」标签,之后可按标签筛选复习
    const data = await vocabularyApi.fetchWords({ q: word, page_size: 5 })
    const target = data.items.find((w) => w.word.toLowerCase() === word.toLowerCase())
    if (!target) {
      ElMessage.warning('未在单词本中找到该单词')
      return
    }
    const tags = [...new Set([...(target.tags || []), '易错'])]
    await vocabularyApi.updateWord(target.id, { tags })
    ElMessage.success(`已将「${word}」标记为易错`)
  } catch {} finally {
    addingWords.value.delete(word)
  }
}

function reset() {
  store.resetQuiz()
  answers.value = []
  currentIndex.value = 0
  step.value = 'setup'
}
</script>

<template>
  <div class="quiz-view">
    <BackendOffline v-if="backendStore.online === false" style="margin-bottom: 16px" />

    <!-- 设置页 -->
    <el-card v-if="step === 'setup'" class="setup-card">
      <h2 class="title">单词自测</h2>
      <p class="desc">根据中文释义选出正确的英文单词,测测你的掌握程度</p>
      <div class="setup-row">
        <span class="label">题量</span>
        <el-radio-group v-model="count">
          <el-radio-button :value="5">5 题</el-radio-button>
          <el-radio-button :value="10">10 题</el-radio-button>
          <el-radio-button :value="20">20 题</el-radio-button>
        </el-radio-group>
      </div>
      <el-button
        type="primary"
        size="large"
        :loading="loading"
        :disabled="backendStore.online === false"
        @click="start"
      >
        开始自测
      </el-button>
    </el-card>

    <!-- 答题页 -->
    <template v-else-if="step === 'answering' && currentQuestion">
      <el-card class="question-card">
        <div class="question-head">
          <span class="q-index">第 {{ currentIndex + 1 }} / {{ questions.length }} 题</span>
          <el-button link type="info" @click="reset">退出</el-button>
        </div>
        <div class="q-word">{{ currentQuestion.word }}</div>
        <div v-if="currentQuestion.phonetic" class="q-phonetic">/{{ currentQuestion.phonetic }}/</div>
        <el-radio-group
          v-model="answers[currentIndex].answer_index"
          class="q-options"
        >
          <el-radio v-for="(opt, i) in currentQuestion.options" :key="i" :value="i" border class="q-option">
            {{ opt }}
          </el-radio>
        </el-radio-group>
        <div class="q-actions">
          <el-button :disabled="currentIndex === 0" @click="prev">上一题</el-button>
          <el-button v-if="!isLast" type="primary" :disabled="answers[currentIndex].answer_index === null" @click="next">
            下一题
          </el-button>
          <el-popconfirm v-else title="确认交卷?" :disabled="!allAnswered" @confirm="submit">
            <template #reference>
              <el-button type="success" :loading="loading" :disabled="!allAnswered">交卷</el-button>
            </template>
          </el-popconfirm>
        </div>
      </el-card>
    </template>

    <!-- 结果页 -->
    <template v-else-if="step === 'result' && results">
      <el-card class="result-card">
        <div class="result-head">
          <el-progress
            type="circle"
            :percentage="scorePercent"
            :width="110"
            :color="scoreColor(scorePercent / 100)"
          >
            <template #default>
              <div class="result-score">{{ results.score }}/{{ results.total }}</div>
            </template>
          </el-progress>
          <div class="result-info">
            <h2>自测完成!</h2>
            <p>答错 {{ results.total - results.score }} 题</p>
          </div>
        </div>

        <template v-if="wrongResults.length">
          <h3 class="wrong-title">错题回顾</h3>
          <!-- 窄屏卡片化(4 列表格手机上放不下) -->
          <div v-if="isXs" class="wrong-cards">
            <div v-for="r in wrongResults" :key="r.word" class="wrong-card">
              <div class="wrc-head">
                <b class="wrc-word">{{ r.word }}</b>
                <el-button
                  link
                  type="primary"
                  size="small"
                  :loading="addingWords.has(r.word)"
                  @click="markHard(r.word)"
                >
                  标记易错
                </el-button>
              </div>
              <div class="wrc-line">你的答案:<span class="wrong-answer">{{ r.your_answer }}</span></div>
              <div class="wrc-line">正确答案:<span class="right-answer">{{ r.correct_answer }}</span></div>
            </div>
          </div>
          <el-table v-else :data="wrongResults" size="small">
            <el-table-column prop="word" label="单词" width="150" />
            <el-table-column prop="your_answer" label="你的答案" width="160">
              <template #default="{ row }">
                <span class="wrong-answer">{{ row.your_answer }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="correct_answer" label="正确答案" width="160">
              <template #default="{ row }">
                <span class="right-answer">{{ row.correct_answer }}</span>
              </template>
            </el-table-column>
            <el-table-column label="操作">
              <template #default="{ row }">
                <el-button
                  link
                  type="primary"
                  :loading="addingWords.has(row.word)"
                  @click="markHard(row.word)"
                >
                  标记易错
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </template>

        <div class="result-actions">
          <el-button type="primary" @click="reset">再测一次</el-button>
        </div>
      </el-card>
    </template>
  </div>
</template>

<style scoped>
.setup-card,
.question-card,
.result-card {
  max-width: 640px;
  margin: 0 auto;
}
.title {
  margin: 0 0 8px;
}
.desc {
  color: var(--el-text-color-secondary);
  margin: 0 0 20px;
  font-size: 14px;
}
.setup-row {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 24px;
}
.label {
  color: var(--el-text-color-secondary);
  font-size: 14px;
}
.question-head {
  display: flex;
  justify-content: space-between;
  margin-bottom: 20px;
}
.q-index {
  color: var(--el-text-color-secondary);
  font-size: 13px;
}
.q-word {
  font-size: 32px;
  font-weight: 700;
  text-align: center;
}
.q-phonetic {
  text-align: center;
  color: var(--el-text-color-secondary);
  margin-bottom: 20px;
}
.q-options {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.q-option {
  width: 100%;
  height: auto;
  padding: 10px 14px;
  justify-content: flex-start;
  font-size: 15px;
}
.q-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 24px;
}
.result-head {
  display: flex;
  align-items: center;
  gap: 24px;
}
.result-score {
  font-size: 20px;
  font-weight: 700;
}
.result-info h2 {
  margin: 0 0 4px;
}
.result-info p {
  margin: 0;
  color: var(--el-text-color-secondary);
}
.wrong-title {
  margin: 24px 0 10px;
  font-size: 15px;
}
.wrong-answer {
  color: var(--el-color-danger);
}
.right-answer {
  color: var(--el-color-success);
}
.result-actions {
  margin-top: 20px;
  text-align: center;
}

/* ---- 窄屏错题卡片 ---- */
.wrong-cards {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.wrong-card {
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  padding: 10px 14px;
}
.wrc-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  flex-wrap: wrap;
}
.wrc-word {
  font-size: 16px;
}
.wrc-line {
  margin-top: 6px;
  font-size: 14px;
  color: var(--el-text-color-regular);
}

/* 窄屏:选项/操作按钮换行与间距微调 */
@media (max-width: 767px) {
  .q-options {
    gap: 8px;
  }
  .q-actions {
    flex-wrap: wrap;
    gap: 8px;
  }
  .result-head {
    flex-wrap: wrap;
    gap: 12px;
  }
}
</style>
