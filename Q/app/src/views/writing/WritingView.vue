<script setup>
import { ref, reactive, computed, watch, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useWritingStore } from '@/stores/writing'
import { useBackendStore } from '@/stores/backend'
import BackendOffline from '@/components/common/BackendOffline.vue'
import EssayResultPanel from '@/components/writing/EssayResultPanel.vue'
import { writingApi } from '@/api/writing'
import { useIsXs } from '@/composables/useMediaQuery'
import { WRITING_STAGES } from '@/constants'
import { formatDateTime } from '@/utils/format'

const store = useWritingStore()
const backendStore = useBackendStore()

// 窄屏:steps 简化为 simple 模式、批量解析预览表卡片化
const isXs = useIsXs()

const step = ref(1) // 1 选题, 2 写作, 3 结果
const topics = ref([])
const topicsLoading = ref(false)
const stageFilter = ref('')
const selectedTopic = ref(null)
const form = reactive({ title: '', content: '', requirement: '' })
const grading = ref(false)
const currentResult = ref(null)
const currentTopicTitle = ref('')
const currentStage = ref('')

// 自定义题目:手动添加 / 批量导入(AI 整理)
const importDialogVisible = ref(false)
const importTab = ref('single')
const manualForm = reactive({ title: '', stage: 'junior', prompt: '', keywords: '' })
const addingTopic = ref(false)
const batchText = ref('')
const parsing = ref(false)
const parsedTopics = ref([])
const importingTopics = ref(false)

// 题目自定义分组:筛选 + 管理 + 题目归属
const topicGroups = ref([])
const groupFilter = ref('')
const groupDialogVisible = ref(false)
const newGroupName = ref('')
const creatingGroup = ref(false)
const assignDialogVisible = ref(false)
const assignTopic = ref(null)
const assignGroups = ref([])
const savingGroups = ref(false)

async function loadTopicGroups() {
  try {
    topicGroups.value = (await writingApi.fetchTopicGroups()).groups || []
  } catch {
    // 错误已由 request.js 统一提示
  }
}

async function handleCreateGroup() {
  const name = newGroupName.value.trim()
  if (!name || creatingGroup.value) return
  creatingGroup.value = true
  try {
    await writingApi.createTopicGroup(name)
    ElMessage.success(`分组「${name}」已创建`)
    newGroupName.value = ''
    await loadTopicGroups()
  } catch {
    // 错误已由 request.js 统一提示(含 409 重名)
  } finally {
    creatingGroup.value = false
  }
}

async function handleDeleteGroup(group) {
  try {
    await ElMessageBox.confirm(
      `确定删除分组「${group.name}」吗?该分组下的 ${group.count} 道题目不会被删除,只是移出分组。`,
      '删除分组',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  try {
    await writingApi.deleteTopicGroup(group.name)
    ElMessage.success(`分组「${group.name}」已删除`)
    if (groupFilter.value === group.name) {
      groupFilter.value = ''
    }
    // 无论当前筛选如何都重拉题目,否则卡片上的已删除分组标签不刷新
    await fetchTopics()
    await loadTopicGroups()
  } catch {
    // 错误已由 request.js 统一提示
  }
}

function openAssignDialog(topic) {
  assignTopic.value = topic
  assignGroups.value = [...(topic.groups || [])]
  assignDialogVisible.value = true
}

async function handleSaveAssign() {
  if (!assignTopic.value || savingGroups.value) return
  savingGroups.value = true
  try {
    const updated = await writingApi.updateTopic(assignTopic.value.id, { groups: assignGroups.value })
    assignTopic.value.groups = updated.groups
    const idx = topics.value.findIndex((t) => t.id === updated.id)
    if (idx !== -1) topics.value[idx] = updated
    assignDialogVisible.value = false
    ElMessage.success('分组已保存')
    await loadTopicGroups()
    if (groupFilter.value) await fetchTopics()
  } catch {
    // 错误已由 request.js 统一提示
  } finally {
    savingGroups.value = false
  }
}

const LEVEL_TO_STAGE = { A1: 'primary', A2: 'primary', B1: 'junior', B2: 'senior', C1: 'senior' }

function stageLabelOf(value) {
  const found = WRITING_STAGES.find((s) => s.value === value)
  return found ? found.label : ''
}

async function handleAddTopic() {
  if (!manualForm.title.trim() || !manualForm.prompt.trim() || addingTopic.value) return
  addingTopic.value = true
  try {
    const keywords = manualForm.keywords
      .split(/[,，]/)
      .map((k) => k.trim())
      .filter(Boolean)
    await writingApi.addTopic({
      title: manualForm.title.trim(),
      stage: manualForm.stage,
      prompt: manualForm.prompt.trim(),
      keywords,
    })
    ElMessage.success(`题目「${manualForm.title.trim()}」已添加`)
    manualForm.title = ''
    manualForm.prompt = ''
    manualForm.keywords = ''
    importDialogVisible.value = false
    await fetchTopics()
  } catch {
    // 错误已由 request.js 统一提示(含 409 重名)
  } finally {
    addingTopic.value = false
  }
}

async function handleParseTopics() {
  if (!batchText.value.trim() || parsing.value) return
  parsing.value = true
  try {
    const data = await writingApi.parseTopics(batchText.value)
    parsedTopics.value = data.topics || []
    if (!parsedTopics.value.length) {
      ElMessage.warning('未能识别出有效题目,请调整素材格式(每行一个题目)')
    }
  } catch {
    // 错误已提示
  } finally {
    parsing.value = false
  }
}

async function handleImportTopics() {
  if (!parsedTopics.value.length || importingTopics.value) return
  importingTopics.value = true
  try {
    const res = await writingApi.importTopics(parsedTopics.value)
    ElMessage.success(`导入完成:新增 ${res.imported} 题,重复跳过 ${res.skipped} 题`)
    importDialogVisible.value = false
    batchText.value = ''
    parsedTopics.value = []
    await fetchTopics()
  } catch {
    // 错误已提示
  } finally {
    importingTopics.value = false
  }
}

async function handleDeleteTopic(topic) {
  try {
    await ElMessageBox.confirm(
      `确定删除题目「${topic.title}」吗?`,
      '删除题目',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  try {
    await writingApi.deleteTopic(topic.id)
    ElMessage.success('题目已删除')
    if (selectedTopic.value?.id === topic.id) {
      selectedTopic.value = null
    }
    await fetchTopics()
  } catch {
    // 错误已提示
  }
}

let draftTimer = null

onMounted(async () => {
  await fetchTopics()
  loadTopicGroups()
  // 恢复草稿(刷新不丢)
  form.title = store.draft.title || ''
  form.content = store.draft.content || ''
  form.requirement = store.draft.requirement || ''
  if (store.draft.topicId) {
    // 优先从已加载的题目里找回完整对象(缺 prompt/stage 会导致写作页
    // 题目提示空白、批改缺少学段参照);找不到(如已删除)再退回部分对象
    const full = topics.value.find((t) => t.id === store.draft.topicId)
    selectedTopic.value = full || { id: store.draft.topicId, title: store.draft.topicTitle }
  }
})

async function fetchTopics() {
  topicsLoading.value = true
  try {
    const data = await writingApi.fetchTopics(
      stageFilter.value || undefined,
      groupFilter.value || undefined,
    )
    topics.value = data.topics || []
  } catch {
    // 错误已提示
  } finally {
    topicsLoading.value = false
  }
}

function pickRandom() {
  if (!topics.value.length) return
  selectedTopic.value = topics.value[Math.floor(Math.random() * topics.value.length)]
}

// 草稿自动保存(500ms 防抖 → localStorage)
watch(
  () => [form.title, form.content, form.requirement, selectedTopic.value],
  () => {
    clearTimeout(draftTimer)
    draftTimer = setTimeout(() => {
      store.saveDraft({
        title: form.title,
        content: form.content,
        requirement: form.requirement,
        topicId: selectedTopic.value?.id || '',
        topicTitle: selectedTopic.value?.title || '',
      })
    }, 500)
  },
  { deep: true },
)

async function submitGrade() {
  if (!form.content.trim() || grading.value) return
  grading.value = true
  try {
    currentResult.value = await store.grade(
      {
        topic_id: selectedTopic.value?.id || null,
        title: form.title,
        content: form.content,
        requirement: form.requirement,
        stage: selectedTopic.value?.stage || undefined,
      },
      {
        topicTitle: selectedTopic.value?.title || '',
        stage: selectedTopic.value?.stage || '',
      },
    )
    currentTopicTitle.value = selectedTopic.value?.title || ''
    currentStage.value = selectedTopic.value?.stage || ''
    step.value = 3
    // 已提交:清空正文与批改要求草稿,避免误重复提交/下篇带上篇要求(记录中可随时回看)
    form.title = ''
    form.content = ''
    form.requirement = ''
    store.saveDraft({ title: '', content: '', requirement: '' })
  } catch {
    // 错误已提示
  } finally {
    grading.value = false
  }
}

function loadRecord(record) {
  selectedTopic.value = record.topic
    ? { id: record.topic, title: record.topicTitle, stage: record.stage || '' }
    : null
  form.title = record.title || ''
  form.content = record.content || ''
  form.requirement = record.requirement || ''
  currentResult.value = record.result
  currentTopicTitle.value = record.topicTitle || ''
  currentStage.value = record.stage || ''
  step.value = 3
}

function editAgain() {
  // 回到写作步(内容保留在表单中)
  step.value = 2
}

function startNew() {
  selectedTopic.value = null
  form.title = ''
  form.content = ''
  form.requirement = ''
  currentResult.value = null
  currentStage.value = ''
  step.value = 1
}

const canSubmit = computed(() => form.content.trim().length > 0)
</script>

<template>
  <div class="writing-view">
    <BackendOffline v-if="backendStore.online === false" style="margin-bottom: 16px" />

    <el-steps :active="step - 1" finish-status="success" class="steps" :simple="isXs">
      <el-step title="选择题目" />
      <el-step title="写作" />
      <el-step title="批改结果" />
    </el-steps>

    <el-row :gutter="20" class="content-row">
      <el-col :xs="24" :lg="17">
        <!-- 第一步:选题 -->
        <el-card v-if="step === 1">
          <div class="topic-toolbar">
            <div class="toolbar-left">
              <span class="label">学段筛选</span>
              <el-select v-model="stageFilter" placeholder="全部" clearable class="stage-select" @change="fetchTopics">
                <el-option
                  v-for="s in WRITING_STAGES"
                  :key="s.value"
                  :label="`${s.label}(${s.hint})`"
                  :value="s.value"
                />
              </el-select>
              <el-select v-model="groupFilter" placeholder="按分组筛选" clearable class="group-select" @change="fetchTopics">
                <el-option
                  v-for="g in topicGroups"
                  :key="g.name"
                  :label="`${g.name}(${g.count})`"
                  :value="g.name"
                />
              </el-select>
            </div>
            <div class="toolbar-right">
              <el-button type="primary" plain @click="importDialogVisible = true">
                <el-icon><EditPen /></el-icon>自定义题目
              </el-button>
              <el-button plain @click="groupDialogVisible = true">
                <el-icon><CollectionTag /></el-icon>分组管理
              </el-button>
              <el-button :disabled="!topics.length" @click="pickRandom">
                <el-icon><Refresh /></el-icon>随机一题
              </el-button>
            </div>
          </div>

          <div v-loading="topicsLoading" class="topic-list">
            <div
              v-for="t in topics"
              :key="t.id"
              class="topic-item"
              :class="{ selected: selectedTopic?.id === t.id }"
              @click="selectedTopic = t"
            >
              <div class="topic-head">
                <span class="topic-title">{{ t.title }}</span>
                <div class="topic-tags">
                  <el-tag v-for="g in t.groups || []" :key="g" size="small" type="warning">{{ g }}</el-tag>
                  <el-tag size="small" type="primary">{{ stageLabelOf(t.stage) || t.level }}</el-tag>
                  <el-tag size="small" type="info">{{ t.level }}</el-tag>
                  <el-button link type="primary" size="small" class="topic-del" title="加入分组" @click.stop="openAssignDialog(t)">
                    <el-icon><CollectionTag /></el-icon>
                  </el-button>
                  <el-popconfirm title="删除该题目?" @confirm="handleDeleteTopic(t)">
                    <template #reference>
                      <el-button link type="danger" size="small" class="topic-del" @click.stop>
                        <el-icon><Delete /></el-icon>
                      </el-button>
                    </template>
                  </el-popconfirm>
                </div>
              </div>
              <div class="topic-prompt">{{ t.prompt }}</div>
              <div v-if="t.keywords?.length" class="topic-keywords">
                关键词:
                <el-tag v-for="k in t.keywords" :key="k" size="small" type="warning" class="kw-tag">{{ k }}</el-tag>
              </div>
            </div>
            <el-empty v-if="!topicsLoading && !topics.length" description="暂无题目(后端离线或题库为空)">
              <el-button :disabled="backendStore.online === false" @click="fetchTopics">重新加载</el-button>
            </el-empty>
          </div>

          <div class="topic-actions">
            <el-button type="primary" :disabled="!selectedTopic" @click="step = 2">
              开始写作
            </el-button>
          </div>
        </el-card>

        <!-- 第二步:写作 -->
        <el-card v-else-if="step === 2">
          <div class="topic-reminder" v-if="selectedTopic">
            <b>{{ selectedTopic.title }}</b>:{{ selectedTopic.prompt }}
          </div>
          <div class="essay-form">
            <el-input v-model="form.title" placeholder="作文标题(可选)" class="form-gap" />
            <el-input
              v-model="form.requirement"
              placeholder="批改要求(可选),如:请重点检查时态和冠词的使用"
              class="form-gap"
            />
            <el-input
              v-model="form.content"
              type="textarea"
              :rows="14"
              placeholder="在这里写下你的英语作文…(草稿自动保存,刷新不丢失)"
            />
            <div class="essay-actions">
              <el-button @click="step = 1">返回选题</el-button>
              <el-button
                type="primary"
                :loading="grading"
                :disabled="!canSubmit || backendStore.online === false"
                @click="submitGrade"
              >
                提交批改
              </el-button>
            </div>
            <div v-if="grading" class="grading-hint">
              <el-icon class="is-loading"><Loading /></el-icon>
              AI 正在批改作文,预计 30~60 秒,请稍候…
            </div>
          </div>
        </el-card>

        <!-- 第三步:结果 -->
        <el-card v-else>
          <div class="result-toolbar">
            <div class="result-left">
              <span v-if="currentTopicTitle" class="result-topic">题目:{{ currentTopicTitle }}</span>
              <el-tag v-if="currentStage" size="small" type="primary">{{ stageLabelOf(currentStage) }}学段评分</el-tag>
            </div>
            <div>
              <el-button @click="editAgain">编辑并重新批改</el-button>
              <el-button type="primary" plain @click="startNew">再写一篇</el-button>
            </div>
          </div>
          <EssayResultPanel
            v-if="currentResult"
            :result="currentResult"
            :topic-id="selectedTopic?.id || ''"
          />
        </el-card>

        <!-- 分组管理对话框 -->
        <el-dialog v-model="groupDialogVisible" title="分组管理" width="440px">
          <div class="group-create">
            <el-input
              v-model="newGroupName"
              placeholder="新分组名,如:考试重点 / 日常话题"
              maxlength="20"
              @keyup.enter="handleCreateGroup"
            />
            <el-button
              type="primary"
              :loading="creatingGroup"
              :disabled="!newGroupName.trim()"
              @click="handleCreateGroup"
            >
              创建分组
            </el-button>
          </div>
          <el-scrollbar max-height="320px">
            <div v-for="g in topicGroups" :key="g.name" class="group-item">
              <div class="group-item-main">
                <span class="group-name">{{ g.name }}</span>
                <el-tag size="small" type="info">{{ g.count }} 题</el-tag>
              </div>
              <el-button link type="danger" size="small" @click="handleDeleteGroup(g)">
                <el-icon><Delete /></el-icon>
              </el-button>
            </div>
            <el-empty v-if="!topicGroups.length" description="还没有分组,创建一个吧" :image-size="60" />
          </el-scrollbar>
          <div class="group-hint">题目卡片上的标签图标可把题目加入分组</div>
        </el-dialog>

        <!-- 题目分组归属对话框 -->
        <el-dialog v-model="assignDialogVisible" :title="`题目分组:${assignTopic?.title || ''}`" width="420px">
          <el-select
            v-model="assignGroups"
            multiple
            filterable
            allow-create
            default-first-option
            placeholder="选择或输入新分组名"
            style="width: 100%"
          >
            <el-option v-for="g in topicGroups" :key="g.name" :label="g.name" :value="g.name" />
          </el-select>
          <template #footer>
            <el-button @click="assignDialogVisible = false">取消</el-button>
            <el-button type="primary" :loading="savingGroups" @click="handleSaveAssign">保存</el-button>
          </template>
        </el-dialog>

        <!-- 自定义题目对话框 -->
        <el-dialog v-model="importDialogVisible" title="自定义作文题目" width="580px">
          <el-tabs v-model="importTab">
            <el-tab-pane label="手动添加" name="single">
              <el-form label-width="70px">
                <el-form-item label="题目">
                  <el-input v-model="manualForm.title" placeholder="英文题目,如 My School Life" maxlength="80" />
                </el-form-item>
                <el-form-item label="学段">
                  <el-select v-model="manualForm.stage" style="width: 100%">
                    <el-option
                      v-for="s in WRITING_STAGES"
                      :key="s.value"
                      :label="`${s.label}(${s.hint})`"
                      :value="s.value"
                    />
                  </el-select>
                </el-form-item>
                <el-form-item label="要求">
                  <el-input
                    v-model="manualForm.prompt"
                    type="textarea"
                    :rows="4"
                    placeholder="英文写作要求,如:Write about your school life..."
                  />
                </el-form-item>
                <el-form-item label="关键词">
                  <el-input v-model="manualForm.keywords" placeholder="逗号分隔,如 school, friends, classes" />
                </el-form-item>
              </el-form>
              <div class="import-actions">
                <el-button
                  type="primary"
                  :loading="addingTopic"
                  :disabled="!manualForm.title.trim() || !manualForm.prompt.trim()"
                  @click="handleAddTopic"
                >
                  添加题目
                </el-button>
              </div>
            </el-tab-pane>

            <el-tab-pane label="批量导入(AI 整理)" name="batch">
              <p class="import-tip">
                粘贴题目素材(每行一个,可带中文说明),AI 自动整理成规范的英文题目
              </p>
              <el-input
                v-model="batchText"
                type="textarea"
                :rows="6"
                placeholder="例如:&#10;我的学校生活&#10;环保的重要性&#10;My favorite sport"
              />
              <div class="import-actions">
                <el-button
                  type="primary"
                  :loading="parsing"
                  :disabled="!batchText.trim()"
                  @click="handleParseTopics"
                >
                  AI 解析
                </el-button>
              </div>
              <template v-if="parsedTopics.length">
                <!-- 窄屏卡片化(580 dialog 在小屏实际宽约 100vw-32,3 列放不下) -->
                <div v-if="isXs" class="parsed-cards">
                  <div v-for="(t, i) in parsedTopics" :key="i" class="parsed-item">
                    <div class="pi-head">
                      <b>{{ t.title }}</b>
                      <span class="pi-stage">{{ stageLabelOf(LEVEL_TO_STAGE[t.level] || '') || t.level }}</span>
                    </div>
                    <div class="pi-prompt">{{ t.prompt }}</div>
                  </div>
                </div>
                <el-table v-else :data="parsedTopics" size="small" max-height="260" class="parsed-table">
                  <el-table-column prop="title" label="题目" min-width="150" />
                  <el-table-column label="学段" width="70">
                    <template #default="{ row }">{{ stageLabelOf(LEVEL_TO_STAGE[row.level] || '') || row.level }}</template>
                  </el-table-column>
                  <el-table-column prop="prompt" label="要求" min-width="220" show-overflow-tooltip />
                </el-table>
                <div class="import-actions">
                  <el-button
                    type="primary"
                    :loading="importingTopics"
                    @click="handleImportTopics"
                  >
                    确认导入 {{ parsedTopics.length }} 题
                  </el-button>
                </div>
              </template>
            </el-tab-pane>
          </el-tabs>
        </el-dialog>
      </el-col>

      <el-col :xs="24" :lg="7">
        <el-card class="records-card">
          <template #header>我的作文(本地保存)</template>
          <el-scrollbar class="records-scroll">
            <div v-for="r in store.records" :key="r.id" class="record-item" @click="loadRecord(r)">
              <div class="record-head">
                <span class="record-title">{{ r.topicTitle || r.title || '未命名作文' }}</span>
                <el-tag size="small" :type="r.result.score >= 80 ? 'success' : r.result.score >= 60 ? 'warning' : 'danger'">
                  {{ r.result.score }}分
                </el-tag>
              </div>
              <div class="record-meta">
                <span>{{ formatDateTime(r.createdAt) }}</span>
                <el-popconfirm title="删除该记录?" @confirm="store.removeRecord(r.id)">
                  <template #reference>
                    <el-button link type="danger" size="small" @click.stop>
                      <el-icon><Delete /></el-icon>
                    </el-button>
                  </template>
                </el-popconfirm>
              </div>
            </div>
            <el-empty v-if="!store.records.length" description="还没有批改记录" :image-size="70" />
          </el-scrollbar>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped>
.steps {
  max-width: 640px;
  margin: 0 auto 24px;
}
.topic-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.toolbar-left {
  display: flex;
  align-items: center;
  gap: 10px;
}
.label {
  color: var(--el-text-color-secondary);
  font-size: 14px;
}
.topic-list {
  min-height: 120px;
}
.topic-item {
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  padding: 14px;
  margin-bottom: 10px;
  cursor: pointer;
  transition: border-color 0.2s;
}
.topic-item:hover {
  border-color: var(--el-color-primary-light-5);
}
.topic-item.selected {
  border-color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
}
.topic-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}
.topic-tags {
  display: flex;
  gap: 6px;
  flex-shrink: 0;
  align-items: center;
}
.topic-del {
  opacity: 0;
  transition: opacity 0.2s;
  padding: 0;
}
.topic-item:hover .topic-del {
  opacity: 1;
}
.toolbar-right {
  display: flex;
  align-items: center;
  gap: 10px;
}
.import-tip {
  margin: 0 0 12px;
  font-size: 13px;
  color: var(--el-text-color-secondary);
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
.import-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
}
.parsed-table {
  margin-top: 12px;
}
.topic-title {
  font-weight: 600;
  font-size: 15px;
}
.topic-prompt {
  color: var(--el-text-color-regular);
  font-size: 14px;
}
.topic-keywords {
  margin-top: 8px;
  font-size: 13px;
  color: var(--el-text-color-secondary);
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}
.topic-actions {
  margin-top: 16px;
  text-align: center;
}
.topic-reminder {
  background: var(--el-fill-color-light);
  border-radius: 6px;
  padding: 10px 14px;
  font-size: 14px;
  margin-bottom: 16px;
}
.form-gap {
  margin-bottom: 14px;
}
.essay-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 16px;
}
.grading-hint {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 12px;
  font-size: 13px;
  color: var(--el-color-primary);
}
.result-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  flex-wrap: wrap;
  gap: 10px;
}
.result-topic {
  color: var(--el-text-color-secondary);
  font-size: 14px;
}
.result-left {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.record-item {
  padding: 10px;
  border-radius: 6px;
  cursor: pointer;
  margin-bottom: 6px;
}
.record-item:hover {
  background: var(--el-fill-color-light);
}
.record-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.record-title {
  font-size: 14px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.record-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-top: 4px;
}

/* ---- 响应式适配 ---- */

/* 筛选 select 的宽度从内联样式改为 class(内联样式压不过 media query) */
.stage-select {
  width: 180px;
}
.group-select {
  width: 150px;
}
/* 记录区高度:桌面固定 600px;矮屏收缩(el-scrollbar 的 height prop 是内联样式,改 class 控制) */
.records-scroll {
  height: 600px;
  height: min(600px, 55dvh);
  min-height: 260px;
}
/* 窄屏批量解析预览卡片 */
.parsed-cards {
  max-height: 260px;
  overflow-y: auto;
}
.parsed-item {
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  padding: 10px 12px;
  margin-bottom: 8px;
}
.pi-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.pi-stage {
  font-size: 12px;
  color: var(--el-color-primary);
}
.pi-prompt {
  font-size: 13px;
  color: var(--el-text-color-regular);
  margin-top: 4px;
}

@media (max-width: 767px) {
  .steps {
    max-width: none;
  }
  .topic-toolbar {
    flex-wrap: wrap;
    gap: 10px;
  }
  .toolbar-left,
  .toolbar-right {
    flex-wrap: wrap;
    gap: 8px;
  }
  .stage-select,
  .group-select {
    flex: 1 1 40%;
    width: auto;
    min-width: 130px;
  }
  .topic-head {
    flex-wrap: wrap;
    gap: 6px;
  }
  .topic-tags {
    flex-wrap: wrap;
  }
  /* 触屏无 hover:题目卡操作按钮常显 */
  .topic-del {
    opacity: 1;
  }
  .essay-actions {
    flex-wrap: wrap;
  }
  .topic-reminder {
    font-size: 13px;
  }
  .result-toolbar {
    gap: 8px;
  }
}
</style>
