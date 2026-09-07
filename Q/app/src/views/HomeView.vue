<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useVocabularyStore } from '@/stores/vocabulary'
import { useChatStore } from '@/stores/chat'
import { useTranslateStore } from '@/stores/translate'
import { useWritingStore } from '@/stores/writing'
import { useReadingStore } from '@/stores/reading'
import { useBackendStore } from '@/stores/backend'
import BackendOffline from '@/components/common/BackendOffline.vue'

const router = useRouter()
const vocabularyStore = useVocabularyStore()
const chatStore = useChatStore()
const translateStore = useTranslateStore()
const writingStore = useWritingStore()
const readingStore = useReadingStore()
const backendStore = useBackendStore()

const loaded = ref(false)

onMounted(async () => {
  // 后端数据各自失败不影响总览页渲染
  await Promise.allSettled([
    vocabularyStore.fetchWords(),
    vocabularyStore.fetchDue(true, 1),
    chatStore.fetchSessions(),
  ])
  loaded.value = true
})

// 后端来源的统计离线时显示 '--'
function display(value) {
  if (!loaded.value || backendStore.online === false) return '--'
  return value
}

const stats = computed(() => [
  {
    title: '单词总数',
    value: display(vocabularyStore.total),
    icon: 'Collection',
    color: '#409eff',
    path: '/vocabulary',
  },
  {
    title: '今日待复习',
    value: display(vocabularyStore.dueCount),
    icon: 'AlarmClock',
    color: '#e6a23c',
    path: '/vocabulary/flashcards',
  },
  {
    title: 'AI 对话会话',
    value: display(chatStore.sessions.length),
    icon: 'ChatDotRound',
    color: '#67c23a',
    path: '/chat',
  },
  {
    title: '练习记录(本地)',
    value:
      writingStore.records.length + readingStore.records.length + translateStore.history.length,
    icon: 'Tickets',
    color: '#f56c6c',
    path: '/writing',
  },
])

const modules = [
  {
    title: 'AI 对话',
    desc: '与 AI 教练进行沉浸式英语对话,实时纠正语法与表达',
    icon: 'ChatDotRound',
    path: '/chat',
  },
  {
    title: '单词学习记忆',
    desc: '单词本管理、AI 释义例句、闪卡背诵与间隔重复记忆',
    icon: 'Collection',
    path: '/vocabulary',
  },
  {
    title: '英语翻译',
    desc: '中英互译并深度解析词组、语法点与重点词汇',
    icon: 'Position',
    path: '/translate',
  },
  {
    title: '作文学习',
    desc: 'AI 批改作文:评分、逐句纠错、词汇升级与范文参考',
    icon: 'EditPen',
    path: '/writing',
  },
  {
    title: '阅读理解',
    desc: '按难度生成文章与题目,答题后获得逐题解析',
    icon: 'Reading',
    path: '/reading',
  },
]
</script>

<template>
  <div class="home-view">
    <BackendOffline v-if="backendStore.online === false" style="margin-bottom: 20px" />

    <el-row :gutter="16" class="stats-row">
      <el-col v-for="s in stats" :key="s.title" :xs="12" :sm="12" :md="6">
        <el-card class="stat-card" shadow="hover" @click="router.push(s.path)">
          <div class="stat-body">
            <el-icon :size="30" :color="s.color"><component :is="s.icon" /></el-icon>
            <div class="stat-info">
              <div class="stat-value">{{ s.value }}</div>
              <div class="stat-title">{{ s.title }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <h2 class="section-heading">学习模块</h2>
    <el-row :gutter="16">
      <el-col v-for="m in modules" :key="m.title" :xs="24" :sm="12" :md="8" :lg="8">
        <el-card class="module-card" shadow="hover" @click="router.push(m.path)">
          <div class="module-body">
            <el-icon :size="34" color="var(--el-color-primary)"><component :is="m.icon" /></el-icon>
            <div class="module-title">{{ m.title }}</div>
            <div class="module-desc">{{ m.desc }}</div>
            <el-button text type="primary" class="module-btn">
              进入
              <el-icon><ArrowRight /></el-icon>
            </el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped>
.stat-card {
  cursor: pointer;
}
.stat-body {
  display: flex;
  align-items: center;
  gap: 14px;
}
.stat-value {
  font-size: 24px;
  font-weight: 700;
  line-height: 1.2;
}
.stat-title {
  font-size: 13px;
  color: var(--el-text-color-secondary);
}
.section-heading {
  margin: 28px 0 16px;
  font-size: 18px;
}
.module-card {
  cursor: pointer;
  margin-bottom: 16px;
  transition: transform 0.2s;
}
.module-card:hover {
  transform: translateY(-3px);
}
.module-body {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 8px;
  min-height: 150px;
}
.module-title {
  font-size: 16px;
  font-weight: 600;
}
.module-desc {
  font-size: 13px;
  color: var(--el-text-color-secondary);
  line-height: 1.6;
  flex: 1;
}
.module-btn {
  align-self: flex-end;
  padding: 0;
}
</style>
