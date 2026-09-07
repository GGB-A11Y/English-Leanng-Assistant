import { createRouter, createWebHistory } from 'vue-router'
import { getToken } from '@/utils/token'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    // 认证页:独立于 AppLayout 的顶层路由(meta.public = 无需登录)
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/auth/LoginView.vue'),
      meta: { title: '登录', public: true },
    },
    {
      path: '/reset-password',
      name: 'reset-password',
      component: () => import('@/views/auth/ResetPasswordView.vue'),
      meta: { title: '重置密码', public: true },
    },
    {
      path: '/',
      component: () => import('@/layouts/AppLayout.vue'),
      children: [
        { path: '', redirect: '/dashboard' },
        {
          path: 'dashboard',
          name: 'dashboard',
          component: () => import('@/views/HomeView.vue'),
          meta: { title: '学习总览' },
        },
        {
          path: 'chat',
          name: 'chat',
          component: () => import('@/views/chat/ChatView.vue'),
          meta: { title: 'AI 对话' },
        },
        {
          path: 'vocabulary',
          name: 'vocabulary',
          component: () => import('@/views/vocabulary/VocabularyView.vue'),
          meta: { title: '单词学习' },
        },
        // 注意:静态段 flashcards/quiz 必须排在动态段 :id 之前
        {
          path: 'vocabulary/flashcards',
          name: 'flashcards',
          component: () => import('@/views/vocabulary/FlashcardView.vue'),
          meta: { title: '背诵模式' },
        },
        {
          path: 'vocabulary/quiz',
          name: 'quiz',
          component: () => import('@/views/vocabulary/SelfTestView.vue'),
          meta: { title: '单词自测' },
        },
        {
          path: 'vocabulary/:id',
          name: 'word-detail',
          component: () => import('@/views/vocabulary/WordDetailView.vue'),
          meta: { title: '单词详情' },
        },
        {
          path: 'translate',
          name: 'translate',
          component: () => import('@/views/translate/TranslateView.vue'),
          meta: { title: '英语翻译' },
        },
        {
          path: 'writing',
          name: 'writing',
          component: () => import('@/views/writing/WritingView.vue'),
          meta: { title: '作文学习' },
        },
        {
          path: 'reading',
          name: 'reading',
          component: () => import('@/views/reading/ReadingView.vue'),
          meta: { title: '阅读理解' },
        },
      ],
    },
    { path: '/:pathMatch(.*)*', redirect: '/dashboard' },
  ],
})

// 全局登录守卫:未登录访问受保护页面 → 登录页(带 redirect 回跳);
// 已登录访问登录页 → 首页(重置密码页允许登录态访问,方便改密后继续)
router.beforeEach((to) => {
  const authed = Boolean(getToken())
  if (!to.meta.public && !authed) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }
  if (to.name === 'login' && authed) {
    return '/dashboard'
  }
})

export default router
