<script setup>
import { ref, watch, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useVocabularyStore } from '@/stores/vocabulary'
import { useBackendStore } from '@/stores/backend'
import { vocabularyApi } from '@/api/vocabulary'
import BackendOffline from '@/components/common/BackendOffline.vue'
import { useIsXs } from '@/composables/useMediaQuery'
import { formatDateTime } from '@/utils/format'

const router = useRouter()
const store = useVocabularyStore()
const backendStore = useBackendStore()

// 窄屏(<768px)单词列表由表格切换为卡片
const isXs = useIsXs()

// 列表空态文案(表格与卡片两套模板共用)
const emptyDesc = computed(() => {
  if (store.query) return '没有找到匹配的单词'
  if (store.status === 'unlearned') return '太棒了,没有未学习的单词'
  if (store.status === 'learned') return '还没有已学习的单词,去「开始背诵」完成第一次复习吧'
  return '单词本还是空的,添加你的第一个单词吧'
})

const searchInput = ref('')
const addDialogVisible = ref(false)
const addWordInput = ref('')
const adding = ref(false)

// 内置词库导入(小学/初中/高中必备词汇)
const importDialogVisible = ref(false)
const builtinStages = ref([])
const importStage = ref('')
const importing = ref(false)

// 自定义分组:筛选 + 管理
const groups = ref([])
const groupDialogVisible = ref(false)
const newGroupName = ref('')
const creatingGroup = ref(false)

async function loadGroups() {
  try {
    groups.value = (await vocabularyApi.fetchGroups()).groups || []
  } catch {
    // 错误已由 request.js 统一提示
  }
}

async function loadBuiltin() {
  try {
    builtinStages.value = (await vocabularyApi.fetchBuiltin()).stages || []
  } catch {
    // 错误已由 request.js 统一提示
  }
}

function onGroupFilterChange() {
  store.page = 1
  store.fetchWords().catch(() => {})
}

async function openImportDialog() {
  importDialogVisible.value = true
  if (!builtinStages.value.length) {
    await loadBuiltin()
  }
}

async function handleImport() {
  if (!importStage.value || importing.value) return
  importing.value = true
  try {
    const res = await vocabularyApi.importStage(importStage.value)
    ElMessage.success(`已导入「${res.label}」词库:新增 ${res.imported} 个,已存在跳过 ${res.skipped} 个`)
    importDialogVisible.value = false
    store.page = 1
    store.query = ''
    searchInput.value = ''
    await store.fetchWords()
    await loadBuiltin()
  } catch {
    // 错误已由 request.js 统一提示
  } finally {
    importing.value = false
  }
}

async function handleDeleteStage(stage) {
  try {
    await ElMessageBox.confirm(
      `确定删除「${stage.label}」词库的全部 ${stage.imported} 个单词吗?此操作不可恢复。`,
      '删除词库',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
  } catch {
    return // 用户取消
  }
  try {
    const res = await vocabularyApi.deleteStage(stage.stage)
    ElMessage.success(`已删除 ${res.deleted} 个单词`)
    store.page = 1
    await store.fetchWords()
    await loadBuiltin()
    await loadGroups()
  } catch {
    // 错误已由 request.js 统一提示
  }
}

async function handleCreateGroup() {
  const name = newGroupName.value.trim()
  if (!name || creatingGroup.value) return
  creatingGroup.value = true
  try {
    await vocabularyApi.createGroup(name)
    ElMessage.success(`分组「${name}」已创建`)
    newGroupName.value = ''
    await loadGroups()
  } catch {
    // 错误已由 request.js 统一提示(含 409 重名)
  } finally {
    creatingGroup.value = false
  }
}

async function handleDeleteGroup(group) {
  try {
    await ElMessageBox.confirm(
      `确定删除分组「${group.name}」吗?该分组下的 ${group.count} 个单词不会被删除,只是移出分组。`,
      '删除分组',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  try {
    await vocabularyApi.deleteGroup(group.name)
    ElMessage.success(`分组「${group.name}」已删除`)
    if (store.group === group.name) {
      store.group = ''
      store.page = 1
      store.fetchWords().catch(() => {})
    }
    await loadGroups()
  } catch {
    // 错误已由 request.js 统一提示
  }
}

let searchTimer = null
watch(searchInput, (val) => {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    store.query = val
    store.page = 1
    store.fetchWords().catch(() => {})
  }, 300)
})

onMounted(() => {
  // 恢复上次的搜索词(store.query 常驻内存,否则"框空但列表被过滤")
  searchInput.value = store.query
  store.fetchWords().catch(() => {})
  loadGroups()
})

async function handleAddWord() {
  const word = addWordInput.value.trim()
  if (!word || adding.value) return
  adding.value = true
  try {
    const entry = await store.addWord(word)
    addDialogVisible.value = false
    addWordInput.value = ''
    ElMessage.success(`已添加「${entry.word}」`)
  } catch {
    // 错误已由 request.js 统一提示(含 409 重复添加)
  } finally {
    adding.value = false
  }
}

async function handleDelete(row) {
  try {
    await store.deleteWord(row.id)
    ElMessage.success('已删除')
  } catch {}
}

function goDetail(row) {
  router.push(`/vocabulary/${row.id}`)
}
</script>

<template>
  <div class="vocabulary-view">
    <BackendOffline v-if="backendStore.online === false" style="margin-bottom: 16px" />

    <div class="toolbar">
      <el-input
        v-model="searchInput"
        placeholder="搜索单词…"
        clearable
        class="search-input"
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>
      <el-select
        v-model="store.group"
        placeholder="按分组筛选"
        clearable
        class="group-select"
        :disabled="backendStore.online === false"
        @change="onGroupFilterChange"
      >
        <el-option
          v-for="g in groups"
          :key="g.name"
          :label="`${g.name}(${g.count})`"
          :value="g.name"
        />
      </el-select>
      <el-select
        v-model="store.status"
        placeholder="学习状态"
        clearable
        class="status-select"
        :disabled="backendStore.online === false"
        @change="onGroupFilterChange"
      >
        <el-option label="已学习" value="learned" />
        <el-option label="未学习" value="unlearned" />
      </el-select>
      <el-button type="primary" :disabled="backendStore.online === false" @click="addDialogVisible = true">
        <el-icon><Plus /></el-icon>添加单词
      </el-button>
      <el-button :disabled="backendStore.online === false" @click="openImportDialog">
        <el-icon><FolderAdd /></el-icon>导入词库
      </el-button>
      <el-button :disabled="backendStore.online === false" @click="groupDialogVisible = true">
        <el-icon><CollectionTag /></el-icon>分组管理
      </el-button>
      <el-button :disabled="backendStore.online === false" @click="router.push('/vocabulary/flashcards')">
        <el-icon><AlarmClock /></el-icon>开始背诵
      </el-button>
      <el-button :disabled="backendStore.online === false" @click="router.push('/vocabulary/quiz')">
        <el-icon><Tickets /></el-icon>自测
      </el-button>
    </div>

    <!-- 窄屏(<768px):卡片列表;宽屏:表格。
         表格带 fixed="right" 操作列会渲染双份 DOM,无法用 CSS 隐藏切换,故用 v-if 双模板 -->
    <div v-if="isXs" v-loading="store.loading" class="word-cards">
      <el-card v-for="row in store.words" :key="row.id" class="word-card-item" shadow="hover">
        <div class="wc-head">
          <el-tag
            :type="row.next_review_at ? 'success' : 'info'"
            size="small"
            effect="light"
          >
            {{ row.next_review_at ? '已学习' : '未学习' }}
          </el-tag>
          <el-link type="primary" class="wc-word" @click="goDetail(row)">{{ row.word }}</el-link>
          <span v-if="row.phonetic" class="wc-phonetic">/{{ row.phonetic }}/</span>
        </div>
        <div class="wc-def">{{ row.definition_cn || '—' }}</div>
        <div class="wc-meta">
          <el-rate :model-value="row.familiarity ?? 0" disabled size="small" />
          <span class="wc-review">下次复习 {{ formatDateTime(row.next_review_at) }}</span>
        </div>
        <div class="wc-actions">
          <el-button link type="primary" size="small" @click="goDetail(row)">详情</el-button>
          <el-popconfirm title="确定删除该单词?" @confirm="handleDelete(row)">
            <template #reference>
              <el-button link type="danger" size="small">删除</el-button>
            </template>
          </el-popconfirm>
        </div>
      </el-card>
      <el-empty v-if="!store.words.length" :description="emptyDesc" :image-size="90" />
    </div>

    <el-table v-else v-loading="store.loading" :data="store.words" style="width: 100%">
      <el-table-column label="单词" min-width="210">
        <template #default="{ row }">
          <el-tag
            :type="row.next_review_at ? 'success' : 'info'"
            size="small"
            effect="light"
            class="status-tag"
          >
            {{ row.next_review_at ? '已学习' : '未学习' }}
          </el-tag>
          <el-link type="primary" @click="goDetail(row)">{{ row.word }}</el-link>
        </template>
      </el-table-column>
      <el-table-column prop="phonetic" label="音标" min-width="120" />
      <el-table-column prop="definition_cn" label="中文释义" min-width="180" show-overflow-tooltip />
      <el-table-column label="熟悉度" width="140">
        <template #default="{ row }">
          <el-rate :model-value="row.familiarity ?? 0" disabled size="small" />
        </template>
      </el-table-column>
      <el-table-column label="下次复习" min-width="150">
        <template #default="{ row }">{{ formatDateTime(row.next_review_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="150" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="goDetail(row)">详情</el-button>
          <el-popconfirm title="确定删除该单词?" @confirm="handleDelete(row)">
            <template #reference>
              <el-button link type="danger">删除</el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
      <template #empty>
        <el-empty :description="emptyDesc" :image-size="90" />
      </template>
    </el-table>

    <div class="pagination">
      <el-pagination
        background
        layout="total, prev, pager, next"
        :total="store.total"
        :current-page="store.page"
        :page-size="store.pageSize"
        @current-change="(p) => { store.page = p; store.fetchWords().catch(() => {}) }"
      />
    </div>

    <el-dialog v-model="addDialogVisible" title="添加单词" width="420px" :close-on-click-modal="!adding">
      <el-input
        v-model="addWordInput"
        placeholder="输入一个英文单词,如 apple"
        :disabled="adding"
        @keyup.enter="handleAddWord"
      />
      <div v-if="adding" class="add-hint">
        <el-icon class="is-loading"><Loading /></el-icon>
        AI 正在生成释义与例句,约需 10 秒,请稍候…
      </div>
      <template #footer>
        <el-button :disabled="adding" @click="addDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="adding" :disabled="!addWordInput.trim()" @click="handleAddWord">
          添加
        </el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="importDialogVisible" title="导入内置词库" width="460px" :close-on-click-modal="!importing">
      <p class="import-tip">选择学段,一键导入必备词汇(自带音标、释义、例句,无需等待 AI 生成)</p>
      <el-radio-group v-model="importStage" class="import-group" v-loading="!builtinStages.length">
        <el-radio
          v-for="s in builtinStages"
          :key="s.stage"
          :value="s.stage"
          class="import-option"
        >
          <div class="import-option-main">
            <span class="import-label">{{ s.label }}</span>
            <span class="import-count">{{ s.count }} 词</span>
          </div>
          <div class="import-desc">{{ s.desc }}</div>
          <div v-if="s.imported" class="import-manage">
            <el-tag size="small" type="success">已导入 {{ s.imported }} 词</el-tag>
            <el-button
              link
              type="danger"
              size="small"
              @click.stop="handleDeleteStage(s)"
            >
              删除已导入的词库
            </el-button>
          </div>
        </el-radio>
      </el-radio-group>
      <template #footer>
        <el-button :disabled="importing" @click="importDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="importing" :disabled="!importStage" @click="handleImport">
          开始导入
        </el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="groupDialogVisible" title="分组管理" width="440px">
      <div class="group-create">
        <el-input
          v-model="newGroupName"
          placeholder="新分组名,如:易错词 / 四级重点"
          maxlength="20"
          @keyup.enter="handleCreateGroup"
        />
        <el-button type="primary" :loading="creatingGroup" :disabled="!newGroupName.trim()" @click="handleCreateGroup">
          创建分组
        </el-button>
      </div>
      <el-scrollbar max-height="320px" class="group-list">
        <div v-for="g in groups" :key="g.name" class="group-item">
          <div class="group-item-main">
            <span class="group-name">{{ g.name }}</span>
            <el-tag size="small" type="info">{{ g.count }} 词</el-tag>
          </div>
          <el-button link type="danger" size="small" @click="handleDeleteGroup(g)">
            <el-icon><Delete /></el-icon>
          </el-button>
        </div>
        <el-empty v-if="!groups.length" description="还没有分组,创建一个吧" :image-size="60" />
      </el-scrollbar>
      <div class="group-hint">在单词详情页「编辑标签与备注」中,可把单词加入分组</div>
    </el-dialog>
  </div>
</template>

<style scoped>
.toolbar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}
.search-input {
  width: 260px;
}
.group-select {
  width: 170px;
}
.status-select {
  width: 120px;
}
.status-tag {
  margin-right: 8px;
}
.add-hint {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 10px;
  font-size: 13px;
  color: var(--el-color-primary);
}
.import-tip {
  margin: 0 0 14px;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}
.import-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
}
.import-option {
  width: 100%;
  height: auto;
  margin: 0;
  padding: 10px 12px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
}
.import-option-main {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.import-label {
  font-weight: 600;
}
.import-count {
  font-size: 12px;
  color: var(--el-color-primary);
}
.import-desc {
  margin-top: 4px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
.import-manage {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 8px;
}
.group-create {
  display: flex;
  gap: 8px;
  margin-bottom: 14px;
}
.group-list {
  max-height: 320px;
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
.pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

/* ---- 窄屏单词卡片列表 ---- */
.word-cards {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.word-card-item :deep(.el-card__body) {
  padding: 12px 14px;
}
.wc-head {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.wc-word {
  font-size: 18px;
  font-weight: 600;
}
.wc-phonetic {
  color: var(--el-text-color-secondary);
  font-size: 13px;
}
.wc-def {
  margin-top: 6px;
  font-size: 14px;
  color: var(--el-text-color-regular);
}
.wc-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 8px;
}
.wc-review {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
.wc-actions {
  display: flex;
  gap: 8px;
  margin-top: 8px;
}

/* ---- 窄屏工具栏:搜索满行、筛选各占约半行 ---- */
@media (max-width: 767px) {
  .toolbar {
    gap: 8px;
  }
  .search-input {
    flex: 1 1 100%;
    width: auto;
  }
  .group-select {
    flex: 1 1 40%;
    width: auto;
  }
  .status-select {
    flex: 1 1 30%;
    width: auto;
  }
  .pagination {
    justify-content: center;
  }
}
</style>
