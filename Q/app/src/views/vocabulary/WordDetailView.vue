<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useVocabularyStore } from '@/stores/vocabulary'
import { useBackendStore } from '@/stores/backend'
import { vocabularyApi } from '@/api/vocabulary'
import WordCard from '@/components/vocabulary/WordCard.vue'
import BackendOffline from '@/components/common/BackendOffline.vue'

const route = useRoute()
const router = useRouter()
const store = useVocabularyStore()
const backendStore = useBackendStore()

const word = ref(null)
const loading = ref(true)
const regenerating = ref(false)
const saving = ref(false)
const editDialogVisible = ref(false)
const editForm = reactive({ tags: [], groups: [], note: '' })
const groupOptions = ref([])

// 浏览过的单词标签累积(store.knownTags)+ 当前词标签,供编辑时快速选择
const allTags = computed(() => {
  const set = new Set(store.knownTags)
  ;(word.value?.tags || []).forEach((t) => set.add(t))
  return [...set]
})

function syncEditForm() {
  editForm.tags = [...(word.value?.tags || [])]
  editForm.groups = [...(word.value?.groups || [])]
  editForm.note = word.value?.note || ''
}

onMounted(async () => {
  // 优先用列表缓存立即渲染,离线时详情仍可看
  const cached = store.words.find((w) => String(w.id) === String(route.params.id))
  if (cached) {
    word.value = cached
    syncEditForm()
  }
  try {
    word.value = await store.getWord(route.params.id)
    syncEditForm()
  } catch {
    // 错误已提示;离线且无缓存时保持空状态
  }
  loading.value = false
  // 分组选项(供编辑时选择)
  vocabularyApi
    .fetchGroups()
    .then((d) => {
      groupOptions.value = (d.groups || []).map((g) => g.name)
    })
    .catch(() => {})
})

async function handleRegenerate() {
  if (regenerating.value) return
  regenerating.value = true
  try {
    word.value = await store.regenerateWord(route.params.id)
    syncEditForm()
    ElMessage.success('已重新生成')
  } catch {} finally {
    regenerating.value = false
  }
}

async function handleSave() {
  if (saving.value) return
  saving.value = true
  try {
    word.value = await store.updateWord(route.params.id, {
      tags: editForm.tags,
      groups: editForm.groups,
      note: editForm.note,
    })
    editDialogVisible.value = false
    ElMessage.success('已保存')
  } catch {} finally {
    saving.value = false
  }
}

async function handleDelete() {
  try {
    await store.deleteWord(route.params.id)
    ElMessage.success('已删除')
    router.push('/vocabulary')
  } catch {}
}
</script>

<template>
  <div class="word-detail">
    <div v-if="loading" class="skeleton-wrap">
      <el-skeleton :rows="10" animated />
    </div>

    <template v-else>
      <BackendOffline v-if="backendStore.online === false && !word" style="margin-bottom: 16px" />

      <template v-if="word">
        <WordCard :word="word" />
        <div class="actions">
          <el-button :loading="regenerating" :disabled="backendStore.online === false" @click="handleRegenerate">
            <el-icon><Refresh /></el-icon>重新生成
          </el-button>
          <el-button @click="editDialogVisible = true">
            <el-icon><Edit /></el-icon>编辑标签与备注
          </el-button>
          <el-popconfirm title="确定删除该单词?" @confirm="handleDelete">
            <template #reference>
              <el-button type="danger" plain :disabled="backendStore.online === false">
                <el-icon><Delete /></el-icon>删除
              </el-button>
            </template>
          </el-popconfirm>
        </div>
      </template>

      <el-empty v-else description="未找到该单词(可能已删除,或后端离线且无缓存)">
        <el-button type="primary" @click="router.push('/vocabulary')">返回单词本</el-button>
      </el-empty>
    </template>

    <el-dialog v-model="editDialogVisible" title="编辑单词" width="480px">
      <el-form label-width="60px">
        <el-form-item label="标签">
          <el-select
            v-model="editForm.tags"
            multiple
            filterable
            allow-create
            default-first-option
            placeholder="输入后回车添加标签"
            style="width: 100%"
          >
            <el-option v-for="t in allTags" :key="t" :label="t" :value="t" />
          </el-select>
        </el-form-item>
        <el-form-item label="分组">
          <el-select
            v-model="editForm.groups"
            multiple
            filterable
            allow-create
            default-first-option
            placeholder="选择或输入新分组(在单词本「分组管理」中创建)"
            style="width: 100%"
          >
            <el-option v-for="g in groupOptions" :key="g" :label="g" :value="g" />
          </el-select>
        </el-form-item>
        <el-form-item label="备注">
          <el-input
            v-model="editForm.note"
            type="textarea"
            :rows="4"
            placeholder="自己的记忆技巧、易错点、联想…"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.skeleton-wrap {
  padding: 20px;
}
.actions {
  display: flex;
  gap: 12px;
  margin-top: 16px;
}
</style>
