<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useBackendStore } from '@/stores/backend'
import { useAuthStore } from '@/stores/auth'
import SideMenu from '@/components/common/SideMenu.vue'

const route = useRoute()
const router = useRouter()
const backendStore = useBackendStore()
const authStore = useAuthStore()

async function handleLogout() {
  await authStore.logout()
  router.push('/login')
}

// 移动端(<992px)抽屉导航;点击菜单项后由 SideMenu 的 @select 关闭
const drawerVisible = ref(false)

const statusInfo = computed(() => {
  if (backendStore.online === null) return { type: 'info', text: '后端检测中' }
  return backendStore.online
    ? { type: 'success', text: '后端在线' }
    : { type: 'danger', text: '后端离线' }
})

onMounted(() => {
  backendStore.startPolling()
  // 刷新后从本地恢复用户信息(不阻塞页面渲染)
  if (authStore.token && !authStore.user) {
    authStore.fetchMe().catch(() => {})
  }
})
onUnmounted(() => backendStore.stopPolling())
</script>

<template>
  <el-container class="layout">
    <!-- 桌面固定侧栏:<992px 由 CSS 隐藏,改用 header 汉堡按钮 + 抽屉 -->
    <el-aside width="220px" class="aside">
      <div class="logo">
        <el-icon :size="26" color="var(--el-color-primary)"><School /></el-icon>
        <span class="logo-text">英语学习助手</span>
      </div>
      <SideMenu />
    </el-aside>

    <el-container class="right">
      <el-header class="header">
        <div class="header-left">
          <el-button class="menu-toggle" link aria-label="打开导航菜单" @click="drawerVisible = true">
            <el-icon :size="20"><Expand /></el-icon>
          </el-button>
          <div class="page-title">{{ route.meta.title || '' }}</div>
        </div>
        <div class="header-right">
          <el-tag
            :type="statusInfo.type"
            effect="light"
            class="status-tag"
            title="点击重新检测后端连接"
            @click="backendStore.checkHealth()"
          >
            {{ statusInfo.text }}
          </el-tag>
          <el-dropdown v-if="authStore.user" @command="handleLogout">
            <span class="user-entry">
              <el-icon><UserFilled /></el-icon>
              <span class="user-email">{{ authStore.user.email }}</span>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="logout">
                  <el-icon><SwitchButton /></el-icon>退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>
      <el-main class="main">
        <RouterView />
      </el-main>
    </el-container>
  </el-container>

  <!-- 移动端导航抽屉(teleport 到 body,:deep 才能命中内部样式) -->
  <el-drawer v-model="drawerVisible" direction="ltr" size="240px" :with-header="false" class="nav-drawer">
    <div class="drawer-logo">
      <el-icon :size="26" color="var(--el-color-primary)"><School /></el-icon>
      <span class="logo-text">英语学习助手</span>
    </div>
    <SideMenu @navigate="drawerVisible = false" />
  </el-drawer>
</template>

<style scoped>
.layout {
  height: 100vh;
  height: 100dvh; /* 移动端地址栏收展不跳动(先 vh 回退,dvh 兜底) */
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
.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  flex: 1;
}
.menu-toggle {
  display: none;
  padding: 0;
}
.page-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.status-tag {
  cursor: pointer;
}
.header-right {
  display: flex;
  align-items: center;
  gap: 14px;
  flex-shrink: 0;
}
.user-entry {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  font-size: 14px;
  color: var(--el-text-color-primary);
  outline: none;
}
.user-email {
  max-width: 180px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.main {
  overflow-y: auto;
  padding: 20px;
}

/* 窄屏(<992px):隐藏固定侧栏,显示汉堡按钮 */
@media (max-width: 991px) {
  .aside {
    display: none;
  }
  .menu-toggle {
    display: inline-flex;
  }
}

/* 手机(<768px):收窄主区留白、隐藏后端状态 tag(总览页有离线横幅兜底)、
 * 邮箱截断收窄,保证 320px 宽度下 header 不溢出 */
@media (max-width: 767px) {
  .main {
    padding: 12px;
  }
  .status-tag {
    display: none;
  }
  .user-email {
    max-width: 120px;
  }
  .page-title {
    font-size: 15px;
  }
}

/* 抽屉:body 默认 20px 内边距清零,放满菜单 */
.nav-drawer :deep(.el-drawer__body) {
  padding: 0;
  display: flex;
  flex-direction: column;
}
.drawer-logo {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 18px 20px;
  font-size: 17px;
  font-weight: 600;
  border-bottom: 1px solid var(--el-border-color-lighter);
}
</style>
