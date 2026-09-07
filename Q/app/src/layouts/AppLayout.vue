<script setup>
import { computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { useBackendStore } from '@/stores/backend'

const route = useRoute()
const backendStore = useBackendStore()

const menuItems = [
  { path: '/dashboard', title: '学习总览', icon: 'DataBoard' },
  { path: '/chat', title: 'AI 对话', icon: 'ChatDotRound' },
  { path: '/vocabulary', title: '单词学习', icon: 'Collection' },
  { path: '/translate', title: '英语翻译', icon: 'Position' },
  { path: '/writing', title: '作文学习', icon: 'EditPen' },
  { path: '/reading', title: '阅读理解', icon: 'Reading' },
]

// 词汇子页(详情/背诵/自测)统一高亮"单词学习"
const activeMenu = computed(() => {
  if (route.path.startsWith('/vocabulary')) return '/vocabulary'
  return route.path
})

const statusInfo = computed(() => {
  if (backendStore.online === null) return { type: 'info', text: '后端检测中' }
  return backendStore.online
    ? { type: 'success', text: '后端在线' }
    : { type: 'danger', text: '后端离线' }
})

onMounted(() => backendStore.startPolling())
onUnmounted(() => backendStore.stopPolling())
</script>

<template>
  <el-container class="layout">
    <el-aside width="220px" class="aside">
      <div class="logo">
        <el-icon :size="26" color="var(--el-color-primary)"><School /></el-icon>
        <span class="logo-text">英语学习助手</span>
      </div>
      <el-menu :default-active="activeMenu" router class="menu">
        <el-menu-item v-for="item in menuItems" :key="item.path" :index="item.path">
          <el-icon><component :is="item.icon" /></el-icon>
          <span>{{ item.title }}</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container class="right">
      <el-header class="header">
        <div class="page-title">{{ route.meta.title || '' }}</div>
        <el-tag
          :type="statusInfo.type"
          effect="light"
          class="status-tag"
          title="点击重新检测后端连接"
          @click="backendStore.checkHealth()"
        >
          {{ statusInfo.text }}
        </el-tag>
      </el-header>
      <el-main class="main">
        <RouterView />
      </el-main>
    </el-container>
  </el-container>
</template>

<style scoped>
.layout {
  height: 100vh;
}
.aside {
  border-right: 1px solid var(--el-border-color-lighter);
  background: var(--el-bg-color);
  display: flex;
  flex-direction: column;
}
.logo {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 18px 20px;
  font-size: 17px;
  font-weight: 600;
}
.logo-text {
  color: var(--el-text-color-primary);
}
.menu {
  border-right: none;
  flex: 1;
}
.right {
  min-width: 0;
}
.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--el-border-color-lighter);
  background: var(--el-bg-color);
}
.page-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}
.status-tag {
  cursor: pointer;
}
.main {
  overflow-y: auto;
  padding: 20px;
}
</style>
