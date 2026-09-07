<script setup>
import { ref, reactive } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const tab = ref('login') // login | register
const loading = ref(false)
const form = reactive({ email: '', password: '', confirm: '' })

async function submit() {
  const email = form.email.trim()
  const password = form.password
  if (!email || !password || loading.value) return
  if (tab.value === 'register' && password !== form.confirm) {
    ElMessage.error('两次输入的密码不一致')
    return
  }
  loading.value = true
  try {
    if (tab.value === 'login') {
      await authStore.login({ email, password })
      ElMessage.success('欢迎回来!')
    } else {
      await authStore.register({ email, password })
      ElMessage.success('注册成功,已自动登录')
    }
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/dashboard'
    router.push(redirect)
  } catch {
    // 错误已由 request.js 统一提示(401 密码错误 / 409 已注册 / 422 校验失败等)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="auth-page">
    <el-card class="auth-card">
      <div class="auth-logo">
        <el-icon :size="30" color="var(--el-color-primary)"><School /></el-icon>
        <span>英语学习助手</span>
      </div>
      <el-tabs v-model="tab" stretch>
        <el-tab-pane label="登录" name="login" />
        <el-tab-pane label="注册" name="register" />
      </el-tabs>
      <el-form label-position="top" @submit.prevent="submit">
        <el-form-item label="邮箱">
          <el-input
            v-model="form.email"
            type="email"
            placeholder="you@example.com"
            :disabled="loading"
            @keyup.enter="submit"
          />
        </el-form-item>
        <el-form-item label="密码(8~128 个字符)">
          <el-input
            v-model="form.password"
            type="password"
            show-password
            placeholder="输入密码"
            :disabled="loading"
            @keyup.enter="submit"
          />
        </el-form-item>
        <el-form-item v-if="tab === 'register'" label="确认密码">
          <el-input
            v-model="form.confirm"
            type="password"
            show-password
            placeholder="再次输入密码"
            :disabled="loading"
            @keyup.enter="submit"
          />
        </el-form-item>
        <el-button
          type="primary"
          class="auth-submit"
          :loading="loading"
          :disabled="!form.email.trim() || !form.password"
          @click="submit"
        >
          {{ tab === 'login' ? '登录' : '注册并登录' }}
        </el-button>
      </el-form>
      <div class="auth-footer">
        <router-link to="/reset-password">忘记密码?</router-link>
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.auth-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--el-bg-color-page, #f5f7fa);
}
.auth-card {
  width: 400px;
  max-width: calc(100vw - 32px);
}
.auth-logo {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-size: 20px;
  font-weight: 600;
  margin: 8px 0 16px;
}
.auth-submit {
  width: 100%;
}
.auth-footer {
  margin-top: 14px;
  text-align: center;
  font-size: 13px;
}
</style>
