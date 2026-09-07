import './assets/main.css'

import { createApp } from 'vue'
import { createPinia } from 'pinia'
import piniaPluginPersistedstate from 'pinia-plugin-persistedstate'
import ElementPlus from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import 'element-plus/dist/index.css'
import 'element-plus/theme-chalk/dark/css-vars.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'

import App from './App.vue'
import router from './router'

const app = createApp(App)

// 状态管理 + 本地持久化(翻译历史、作文草稿等)
const pinia = createPinia()
pinia.use(piniaPluginPersistedstate)
app.use(pinia)

app.use(router)

// Element Plus 全量引入 + 中文 locale
app.use(ElementPlus, { locale: zhCn })

// 全局注册全部图标,模板中可直接使用 <ChatDotRound /> 等
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

// 跟随系统深色模式:给 <html> 添加 dark class 以启用 Element Plus 暗色变量
const darkMedia = window.matchMedia('(prefers-color-scheme: dark)')
const applyTheme = () => {
  document.documentElement.classList.toggle('dark', darkMedia.matches)
}
applyTheme()
darkMedia.addEventListener('change', applyTheme)

app.mount('#app')
