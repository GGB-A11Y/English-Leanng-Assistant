<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

// 侧边导航菜单:桌面固定侧栏与移动端抽屉共用(一份菜单数据、一份高亮逻辑)。
// el-menu router 模式点击即路由跳转;@select 在点击已激活项时也会触发,
// 父组件用该事件关闭抽屉,行为安全。
defineEmits(['navigate'])

const route = useRoute()

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
</script>

<template>
  <el-menu :default-active="activeMenu" router class="menu" @select="$emit('navigate')">
    <el-menu-item v-for="item in menuItems" :key="item.path" :index="item.path">
      <el-icon><component :is="item.icon" /></el-icon>
      <span>{{ item.title }}</span>
    </el-menu-item>
  </el-menu>
</template>

<style scoped>
.menu {
  border-right: none;
  flex: 1;
}
</style>
