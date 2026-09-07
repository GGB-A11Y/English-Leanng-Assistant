import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
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

export default router
