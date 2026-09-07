<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useVocabularyStore } from '@/stores/vocabulary'
import { useBackendStore } from '@/stores/backend'
import FlashcardItem from '@/components/vocabulary/FlashcardItem.vue'
import BackendOffline from '@/components/common/BackendOffline.vue'

const router = useRouter()
const store = useVocabularyStore()
const backendStore = useBackendStore()

const loading = ref(true)
const queue = ref([])
const index = ref(0)
const reviewedCount = ref(0)
const startedEmpty = ref(false)
const finished = ref(false)

const currentWord = computed(() => queue.value[index.value] || null)
const progress = computed(() =>
  queue.value.length ? Math.round((reviewedCount.value / queue.value.length) * 100) : 0,
)

onMounted(async () => {
  try {
    const data = await store.fetchDue(true, 20)
    queue.value = [...(data.items || [])]
    startedEmpty.value = queue.value.length === 0
    finished.value = startedEmpty.value
  } catch {
    // 离线:错误已提示,保持空态
    startedEmpty.value = true
    finished.value = true
  }
  loading.value = false
})

async function handleRated(quality) {
  reviewedCount.value += 1
  try {
    await store.submitReview(currentWord.value.id, quality)
  } catch {
    // 评分失败:该词不会进入复习排期,明确告知用户
    ElMessage.error('评分提交失败,该单词未记录复习进度,请稍后重试')
  }
  if (index.value + 1 >= queue.value.length) {
    finished.value = true
  } else {
    index.value += 1
  }
}
</script>

<template>
  <div class="flashcard-view">
    <BackendOffline v-if="backendStore.online === false" style="margin-bottom: 16px" />

    <div v-if="loading" class="skeleton-wrap">
      <el-skeleton :rows="5" animated />
    </div>

    <template v-else>
      <div v-if="!finished" class="progress-area">
        <el-progress :percentage="progress" :stroke-width="10" :show-text="false" />
        <div class="progress-text">
          本次复习 {{ reviewedCount }}/{{ queue.length }}
          <span v-if="store.dueCount" class="due-note">(今日到期 {{ store.dueCount }} 个)</span>
        </div>
      </div>

      <FlashcardItem v-if="currentWord && !finished" :word="currentWord" @rated="handleRated" />

      <el-result v-else-if="finished && !startedEmpty" icon="success" title="复习完成!">
        <template #sub-title>本次共复习 {{ reviewedCount }} 个单词,记得明天继续哦</template>
        <template #extra>
          <el-button type="primary" @click="router.push('/vocabulary')">返回单词本</el-button>
        </template>
      </el-result>

      <el-empty v-else description="太棒了,今天没有需要复习的单词!">
        <el-button type="primary" @click="router.push('/vocabulary')">返回单词本</el-button>
      </el-empty>
    </template>
  </div>
</template>

<style scoped>
.skeleton-wrap {
  padding: 20px;
}
.progress-area {
  max-width: 420px;
  margin: 0 auto 8px;
  text-align: center;
}
.progress-text {
  margin-top: 8px;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}
.due-note {
  margin-left: 8px;
}
</style>
