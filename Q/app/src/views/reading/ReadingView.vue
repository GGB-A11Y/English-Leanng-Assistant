<script setup>
import { ref, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useReadingStore } from '@/stores/reading'
import { useBackendStore } from '@/stores/backend'
import BackendOffline from '@/components/common/BackendOffline.vue'
import MarkdownBlock from '@/components/common/MarkdownBlock.vue'
import { READING_STAGES } from '@/constants'
import { formatDateTime, scoreColor } from '@/utils/format'

const store = useReadingStore()
const backendStore = useBackendStore()

const stage = ref('junior')
const topic = ref('')

// 练习记录分组(本地持久化,离线可用)
const groupFilter = ref('')
const groupDialogVisible = ref(false)
const newGroupName = ref('')
const assignDialogVisible = ref(false)
const assignRecord = ref(null)
const assignGroups = ref([])

const allGroupNames = computed(() => {
  const set = new Set(store.recordGroups || [])
  store.records.forEach((r) => (r.groups || []).forEach((g) => set.add(g)))
  return [...set]
})

const groupCounts = computed(() => {
  const counts = {}
  store.records.forEach((r) => (r.groups || []).forEach((g) => (counts[g] = (counts[g] || 0) + 1)))
  return counts
})

const filteredRecords = computed(() => {
  if (!groupFilter.value) return store.records
  return store.records.filter((r) => (r.groups || []).includes(groupFilter.value))
})

function stageLabelOf(value) {
  const found = READING_STAGES.find((s) => s.value === value)
  return found ? found.label : ''
}

function handleCreateGroup() {
  const name = newGroupName.value.trim()
  if (!name) return
  if (store.recordGroups.includes(name)) {
    ElMessage.warning('分组已存在')
    return
  }
  store.addRecordGroup(name)
  ElMessage.success(`分组「${name}」已创建`)
  newGroupName.value = ''
}

async function handleDeleteGroup(name) {
  try {
    await ElMessageBox.confirm(
      `确定删除分组「${name}」吗?分组下的 ${groupCounts.value[name] || 0} 条记录不会被删除,只是移出分组。`,
      '删除分组',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  store.removeRecordGroup(name)
  if (groupFilter.value === name) groupFilter.value = ''
  ElMessage.success(`分组「${name}」已删除`)
}

function openAssignDialog(record) {
  assignRecord.value = record
  assignGroups.value = [...(record.groups || [])]
  assignDialogVisible.value = true
}

function handleSaveAssign() {
  if (!assignRecord.value) return
  store.setRecordGroups(assignRecord.value.id, assignGroups.value)
  assignDialogVisible.value = false
  ElMessage.success('分组已保存')
}
const generating = ref(false)
const submitting = ref(false)
const activeHistory = ref([])

// 进行中的文章保存在内存(store.current 不持久化),刷新后从练习记录回看
const current = computed(() => store.current)
const questions = computed(() => current.value?.article.questions || [])
const allAnswered = computed(() =>
  questions.value.every((q) => current.value?.answers[q.id] != null),
)
const result = computed(() => current.value?.result || null)
const scorePercent = computed(() =>
  result.value ? Math.round((result.value.score / result.value.total) * 100) : 0,
)

async function generate() {
  if (generating.value) return
  generating.value = true
  try {
    await store.generate(stage.value, topic.value.trim())
  } catch {
    // 错误已提示
  } finally {
    generating.value = false
  }
}

async function submit() {
  if (submitting.value || !allAnswered.value) return
  submitting.value = true
  try {
    await store.submit()
  } catch {
    // 错误已提示
  } finally {
    submitting.value = false
  }
}

function newArticle() {
  store.reset()
}

function resultOfRecord(questionId, record) {
  return (record.result?.results || []).find((r) => r.question_id === questionId)
}
</script>

<template>
  <div class="reading-view">
    <BackendOffline v-if="backendStore.online === false" style="margin-bottom: 16px" />

    <!-- 生成区 -->
    <el-card v-if="!current" class="generate-card">
      <h2 class="title">阅读理解练习</h2>
      <p class="desc">AI 按你选择的难度与主题生成文章和题目,答题后获得逐题解析</p>
      <div class="generate-form">
        <div class="form-row">
          <span class="label">学段</span>
          <el-select v-model="stage" class="stage-select">
            <el-option
              v-for="s in READING_STAGES"
              :key="s.value"
              :label="`${s.label}(${s.hint})`"
              :value="s.value"
            />
          </el-select>
        </div>
        <div class="form-row">
          <span class="label">主题</span>
          <el-input v-model="topic" placeholder="可选,如 technology / travel / health" maxlength="100" class="topic-input" />
        </div>
        <el-button
          type="primary"
          size="large"
          :loading="generating"
          :disabled="backendStore.online === false"
          @click="generate"
        >
          生成文章
        </el-button>
        <div v-if="generating" class="gen-hint">
          <el-icon class="is-loading"><Loading /></el-icon>
          AI 正在撰写文章与题目,约需 30 秒,请稍候…
        </div>
      </div>
    </el-card>

    <template v-else>
      <div class="article-toolbar">
        <el-tag type="primary">{{ stageLabelOf(current.article.stage) || current.article.level }} · {{ current.article.word_count }} 词</el-tag>
        <el-button v-if="current.submitted" type="primary" plain @click="newArticle">再做一篇</el-button>
        <el-button v-else @click="newArticle">放弃并重新生成</el-button>
      </div>

      <!-- 文章 -->
      <el-card class="article-card">
        <h2 class="article-title">{{ current.article.title }}</h2>
        <div class="article-content">
          <p v-for="(para, i) in (current.article.content || '').split('\n').filter(Boolean)" :key="i">
            {{ para }}
          </p>
        </div>
        <template v-if="current.article.vocabulary_notes?.length">
          <div class="vocab-notes">
            <span class="label">词汇注释:</span>
            <el-tag v-for="(v, i) in current.article.vocabulary_notes" :key="i" type="info" size="small" class="vocab-tag">
              {{ v.word }} — {{ v.meaning }}
            </el-tag>
          </div>
        </template>
      </el-card>

      <!-- 答题区 -->
      <el-card v-if="!current.submitted" class="question-area">
        <h3 class="section-title">题目({{ questions.length }} 题)</h3>
        <div v-for="(q, i) in questions" :key="q.id" class="question-item">
          <div class="q-title">
            <span class="q-index">{{ i + 1 }}.</span>
            <span>{{ q.question }}</span>
            <el-tag v-if="q.type === 'true_false'" size="small" type="info">判断</el-tag>
            <el-tag v-else size="small" type="info">单选</el-tag>
          </div>
          <el-radio-group :model-value="current.answers[q.id]" @update:model-value="(v) => store.answer(q.id, v)">
            <el-radio v-for="(opt, oi) in q.options" :key="oi" :value="opt" class="q-option">
              {{ opt }}
            </el-radio>
          </el-radio-group>
        </div>
        <div class="submit-area">
          <el-popconfirm title="确认交卷?" :disabled="!allAnswered" @confirm="submit">
            <template #reference>
              <el-button type="success" size="large" :loading="submitting" :disabled="!allAnswered">
                交卷
              </el-button>
            </template>
          </el-popconfirm>
        </div>
      </el-card>

      <!-- 结果区 -->
      <el-card v-else class="result-area">
        <div class="result-head">
          <el-progress
            type="circle"
            :percentage="scorePercent"
            :width="110"
            :color="scoreColor(scorePercent / 100)"
          >
            <template #default>
              <div class="result-score">{{ result.score }}/{{ result.total }}</div>
            </template>
          </el-progress>
          <h3>答题完成!</h3>
        </div>
        <div v-for="(q, i) in questions" :key="q.id" class="result-question" :class="{ wrong: !resultOfRecord(q.id, current)?.correct }">
          <div class="q-title">
            <span class="q-index">{{ i + 1 }}.</span>
            <span>{{ q.question }}</span>
            <el-tag v-if="resultOfRecord(q.id, current)?.correct" size="small" type="success">正确</el-tag>
            <el-tag v-else size="small" type="danger">错误</el-tag>
          </div>
          <div class="answer-detail">
            <div>你的答案:<b>{{ resultOfRecord(q.id, current)?.your_answer }}</b></div>
            <div v-if="!resultOfRecord(q.id, current)?.correct">
              正确答案:<b class="right">{{ resultOfRecord(q.id, current)?.correct_answer }}</b>
            </div>
          </div>
          <div v-if="resultOfRecord(q.id, current)?.explanation" class="explanation">
            <MarkdownBlock :content="resultOfRecord(q.id, current).explanation" />
          </div>
        </div>
      </el-card>
    </template>

    <!-- 历史记录 -->
    <el-card v-if="store.records.length" class="history-card">
      <template #header>
        <div class="history-head">
          <span>练习记录(本地保存)</span>
          <div class="history-head-right">
            <el-select v-model="groupFilter" placeholder="按分组筛选" clearable size="small" style="width: 150px">
              <el-option
                v-for="g in allGroupNames"
                :key="g"
                :label="`${g}(${groupCounts[g] || 0})`"
                :value="g"
              />
            </el-select>
            <el-button size="small" plain @click="groupDialogVisible = true">
              <el-icon><CollectionTag /></el-icon>分组管理
            </el-button>
          </div>
        </div>
      </template>
      <el-collapse v-model="activeHistory">
        <el-collapse-item v-for="r in filteredRecords" :key="r.id" :name="r.id">
          <template #title>
            <div class="history-title">
              <span>{{ r.article.title }}</span>
              <el-tag v-for="g in r.groups || []" :key="g" size="small" type="warning">{{ g }}</el-tag>
              <el-tag size="small" type="info">{{ stageLabelOf(r.article.stage) || r.article.level }}</el-tag>
              <span class="history-meta">{{ formatDateTime(r.createdAt) }}</span>
              <span class="history-score" :style="{ color: scoreColor(r.result.score / r.result.total) }">
                {{ r.result.score }}/{{ r.result.total }}
              </span>
            </div>
          </template>
          <div class="history-body">
            <div class="article-content">
              <p v-for="(para, i) in (r.article.content || '').split('\n').filter(Boolean)" :key="i">{{ para }}</p>
            </div>
            <div v-for="(q, i) in r.article.questions" :key="q.id" class="history-q">
              {{ i + 1 }}. {{ q.question }} —
              <b>我的答案:</b>{{ r.answers[q.id] ?? '未作答' }}
              <template v-if="resultOfRecord(q.id, r)">
                <b :class="{ right: resultOfRecord(q.id, r).correct }">
                  {{ resultOfRecord(q.id, r).correct ? '✓' : '✗' }}
                </b>
              </template>
            </div>
            <div class="history-actions">
              <el-button link type="primary" size="small" @click="openAssignDialog(r)">
                <el-icon><CollectionTag /></el-icon>分组
              </el-button>
              <el-popconfirm title="删除该记录?" @confirm="store.removeRecord(r.id)">
                <template #reference>
                  <el-button link type="danger" size="small">删除记录</el-button>
                </template>
              </el-popconfirm>
            </div>
          </div>
        </el-collapse-item>
      </el-collapse>
      <el-empty
        v-if="!filteredRecords.length && groupFilter"
        description="该分组下暂无练习记录"
        :image-size="60"
      />

      <!-- 分组管理对话框 -->
      <el-dialog v-model="groupDialogVisible" title="分组管理" width="440px">
        <div class="group-create">
          <el-input
            v-model="newGroupName"
            placeholder="新分组名,如:错题本 / 精读文章"
            maxlength="20"
            @keyup.enter="handleCreateGroup"
          />
          <el-button type="primary" :disabled="!newGroupName.trim()" @click="handleCreateGroup">
            创建分组
          </el-button>
        </div>
        <el-scrollbar max-height="320px">
          <div v-for="g in allGroupNames" :key="g" class="group-item">
            <div class="group-item-main">
              <span class="group-name">{{ g }}</span>
              <el-tag size="small" type="info">{{ groupCounts[g] || 0 }} 条</el-tag>
            </div>
            <el-button link type="danger" size="small" @click="handleDeleteGroup(g)">
              <el-icon><Delete /></el-icon>
            </el-button>
          </div>
          <el-empty v-if="!allGroupNames.length" description="还没有分组,创建一个吧" :image-size="60" />
        </el-scrollbar>
        <div class="group-hint">记录展开后点「分组」可把该练习加入分组</div>
      </el-dialog>

      <!-- 记录分组归属对话框 -->
      <el-dialog v-model="assignDialogVisible" title="练习记录分组" width="420px">
        <el-select
          v-model="assignGroups"
          multiple
          filterable
          allow-create
          default-first-option
          placeholder="选择或输入新分组名"
          style="width: 100%"
        >
          <el-option v-for="g in allGroupNames" :key="g" :label="g" :value="g" />
        </el-select>
        <template #footer>
          <el-button @click="assignDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="handleSaveAssign">保存</el-button>
        </template>
      </el-dialog>
    </el-card>
  </div>
</template>

<style scoped>
.generate-card {
  max-width: 640px;
  margin: 0 auto;
}
.title {
  margin: 0 0 8px;
}
.desc {
  color: var(--el-text-color-secondary);
  font-size: 14px;
  margin: 0 0 20px;
}
.form-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 14px;
}
.label {
  color: var(--el-text-color-secondary);
  font-size: 14px;
  width: 44px;
}
.gen-hint {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 12px;
  font-size: 13px;
  color: var(--el-color-primary);
}
.article-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
}
.article-title {
  margin: 0 0 16px;
  text-align: center;
}
.article-content {
  line-height: 1.9;
  font-size: 15px;
}
.article-content p {
  margin: 0 0 12px;
}
.vocab-notes {
  margin-top: 16px;
  padding-top: 14px;
  border-top: 1px dashed var(--el-border-color-lighter);
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
}
.vocab-tag {
  height: auto;
  padding: 4px 8px;
  white-space: normal;
}
.question-area,
.result-area {
  margin-top: 16px;
}
.section-title {
  margin: 0 0 16px;
}
.question-item {
  margin-bottom: 20px;
}
.q-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  margin-bottom: 10px;
  flex-wrap: wrap;
}
.q-index {
  font-weight: 600;
}
.q-option {
  margin-right: 20px;
  margin-bottom: 6px;
  height: auto;
  padding: 6px 0;
}
.submit-area {
  text-align: center;
  margin-top: 8px;
}
.result-head {
  display: flex;
  align-items: center;
  gap: 24px;
  margin-bottom: 8px;
}
.result-score {
  font-size: 20px;
  font-weight: 700;
}
.result-question {
  border: 1px solid var(--el-color-success-light-5);
  border-radius: 8px;
  padding: 14px;
  margin-top: 12px;
}
.result-question.wrong {
  border-color: var(--el-color-danger-light-5);
}
.answer-detail {
  font-size: 14px;
  color: var(--el-text-color-regular);
  margin-bottom: 6px;
}
.right {
  color: var(--el-color-success);
}
.explanation {
  font-size: 14px;
  color: var(--el-text-color-secondary);
}
.history-card {
  margin-top: 16px;
}
.history-title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 14px;
  flex-wrap: wrap;
}
.history-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.history-head-right {
  display: flex;
  align-items: center;
  gap: 8px;
}
.group-create {
  display: flex;
  gap: 8px;
  margin-bottom: 14px;
}
.group-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 10px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  margin-bottom: 8px;
}
.group-item-main {
  display: flex;
  align-items: center;
  gap: 8px;
}
.group-name {
  font-size: 14px;
  font-weight: 600;
}
.group-hint {
  margin-top: 12px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
.history-meta {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}
.history-score {
  font-weight: 600;
}

/* ---- 响应式适配 ---- */

/* 生成表单控件宽度从内联样式改为 class(内联样式压不过 media query) */
.stage-select {
  width: 220px;
}
.topic-input {
  width: 320px;
}

@media (max-width: 767px) {
  .form-row {
    flex-wrap: wrap;
    gap: 8px;
  }
  .stage-select,
  .topic-input {
    width: 100%;
  }
  /* 选项从横排改为整行竖排(触屏更易点按) */
  .q-option {
    margin-right: 0;
    display: flex;
    width: 100%;
    align-items: flex-start;
  }
  .article-toolbar {
    flex-wrap: wrap;
    gap: 10px;
  }
  .history-head {
    flex-wrap: wrap;
    gap: 8px;
  }
  .history-head-right {
    flex-wrap: wrap;
    gap: 8px;
  }
  .result-head {
    flex-wrap: wrap;
  }
}
.history-body {
  font-size: 14px;
}
.history-q {
  margin-bottom: 6px;
}
.history-actions {
  margin-top: 8px;
}
</style>
