<script setup>
import { ref, reactive, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { authApi } from '@/api/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const tab = ref('login') // login | register
const loading = ref(false)
const form = reactive({ email: '', password: '', confirm: '', captchaCode: '' })

// 注册图形验证码(一次性:任何一次校验后即失效,失败后必须换新)
const captcha = ref({ captcha_id: '', image: '' })
const captchaLoading = ref(false)

async function refreshCaptcha() {
  if (captchaLoading.value || loading.value) return
  captchaLoading.value = true
  try {
    captcha.value = await authApi.captcha()
  } catch {
    // 失败置占位(图片位显示「点击刷新」);错误提示已由 request.js 统一 toast
    captcha.value = { captcha_id: '', image: '' }
  } finally {
    captchaLoading.value = false
  }
}

// 进入注册 tab 拉新图;切走时清空输入与图片,避免残留旧输入配新图
watch(tab, (val) => {
  if (val === 'register') {
    refreshCaptcha()
  } else {
    form.captchaCode = ''
    captcha.value = { captcha_id: '', image: '' }
  }
})

async function submit() {
  const email = form.email.trim()
  const password = form.password
  if (!email || !password || loading.value) return
  if (tab.value === 'register' && password !== form.confirm) {
    ElMessage.error('两次输入的密码不一致')
    return
  }
  // Enter 键可绕过按钮 disabled,此处兜底校验验证码非空
  if (tab.value === 'register' && !form.captchaCode.trim()) {
    ElMessage.error('请输入验证码')
    return
  }
  loading.value = true
  let failed = false
  try {
    if (tab.value === 'login') {
      await authStore.login({ email, password })
      ElMessage.success('欢迎回来!')
    } else {
      await authStore.register({
        email,
        password,
        captcha_id: captcha.value.captcha_id,
        captcha_code: form.captchaCode.trim(),
      })
      ElMessage.success('注册成功,已自动登录')
    }
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/dashboard'
    router.push(redirect)
  } catch {
    failed = true
    // 错误已由 request.js 统一提示(401 密码错误 / 409 已注册 / 422 校验失败等)
  } finally {
    loading.value = false
    // 验证码一次性:注册的任何失败(含 409 查重)都已把验证码消费掉,必须换新图;
    // 放在 finally 里刷新:catch 时 loading 未复位,refreshCaptcha 会被自身双锁挡住
    if (failed && tab.value === 'register') {
      form.captchaCode = ''
      refreshCaptcha()
    }
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
        <el-form-item v-if="tab === 'register'" label="验证码">
          <div class="captcha-row">
            <el-input
              v-model="form.captchaCode"
              placeholder="不区分大小写"
              maxlength="4"
              :disabled="loading"
              @keyup.enter="submit"
            />
            <div
              class="captcha-img"
              :class="{ 'is-loading': captchaLoading }"
              title="点击刷新验证码"
              @click="refreshCaptcha"
            >
              <img v-if="captcha.image" :src="captcha.image" alt="验证码,点击刷新" />
              <span v-else>{{ captchaLoading ? '加载中…' : '点击刷新' }}</span>
            </div>
          </div>
        </el-form-item>
        <el-button
          type="primary"
          class="auth-submit"
          :loading="loading"
          :disabled="!form.email.trim() || !form.password || (tab === 'register' && !form.captchaCode.trim())"
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

/* ---- 注册验证码行:输入框自适应,图片固定 120×44(320px 屏下不溢出) ---- */
.captcha-row {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
}
.captcha-row .el-input {
  flex: 1;
  min-width: 0;
}
.captcha-img {
  width: 120px;
  height: 44px;
  flex: none;
  cursor: pointer;
  border: 1px solid var(--el-border-color);
  border-radius: 6px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
.captcha-img img {
  width: 100%;
  height: 100%;
  display: block;
}
.captcha-img.is-loading {
  opacity: 0.5;
  pointer-events: none;
}
.auth-footer {
  margin-top: 14px;
  text-align: center;
  font-size: 13px;
}
</style>
