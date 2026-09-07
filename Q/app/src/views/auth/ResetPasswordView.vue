<script setup>
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { authApi } from '@/api/auth'

const route = useRoute()
const router = useRouter()

// 两段式:无 token → 输入邮箱请求重置邮件;带 ?token= → 设置新密码
const token = computed(() => (typeof route.query.token === 'string' ? route.query.token : ''))

const email = ref('')
const sending = ref(false)
const sent = ref(false)
const newPassword = ref('')
const confirm = ref('')
const submitting = ref(false)

async function requestReset() {
  if (!email.value.trim() || sending.value) return
  sending.value = true
  try {
    const data = await authApi.resetRequest(email.value.trim())
    sent.value = true
    ElMessage.success(data.message)
  } catch {
    // 错误已由 request.js 统一提示(429 限频 / 503 邮件未配置等)
  } finally {
    sending.value = false
  }
}

async function confirmReset() {
  if (!newPassword.value || submitting.value) return
  if (newPassword.value !== confirm.value) {
    ElMessage.error('两次输入的密码不一致')
    return
  }
  submitting.value = true
  try {
    await authApi.resetConfirm({ token: token.value, new_password: newPassword.value })
    ElMessage.success('密码已重置,请用新密码登录')
    router.push('/login')
  } catch {
    // 错误已由 request.js 统一提示(400 链接无效/过期、422 密码校验失败)
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="auth-page">
    <el-card class="auth-card">
      <div class="auth-logo">
        <el-icon :size="30" color="var(--el-color-primary)"><School /></el-icon>
        <span>重置密码</span>
      </div>

      <!-- 第一步:请求重置邮件 -->
      <template v-if="!token">
        <p class="hint">输入注册邮箱,我们会发送一封重置密码邮件</p>
        <el-form label-position="top" @submit.prevent="requestReset">
          <el-form-item label="邮箱">
            <el-input
              v-model="email"
              type="email"
              placeholder="you@example.com"
              :disabled="sending"
              @keyup.enter="requestReset"
            />
          </el-form-item>
          <el-button
            type="primary"
            class="auth-submit"
            :loading="sending"
            :disabled="!email.trim()"
            @click="requestReset"
          >
            发送重置邮件
          </el-button>
        </el-form>
        <div v-if="sent" class="sent-tip">
          邮件已发送(若该邮箱已注册),请查收并按邮件提示操作
        </div>
        <div class="auth-footer">
          <router-link to="/login">返回登录</router-link>
        </div>
      </template>

      <!-- 第二步:设置新密码 -->
      <template v-else>
        <p class="hint">请设置你的新密码(8~128 个字符)</p>
        <el-form label-position="top" @submit.prevent="confirmReset">
          <el-form-item label="新密码">
            <el-input
              v-model="newPassword"
              type="password"
              show-password
              :disabled="submitting"
              @keyup.enter="confirmReset"
            />
          </el-form-item>
          <el-form-item label="确认新密码">
            <el-input
              v-model="confirm"
              type="password"
              show-password
              :disabled="submitting"
              @keyup.enter="confirmReset"
            />
          </el-form-item>
          <el-button
            type="primary"
            class="auth-submit"
            :loading="submitting"
            :disabled="!newPassword"
            @click="confirmReset"
          >
            重置密码
          </el-button>
        </el-form>
      </template>
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
.hint {
  margin: 0 0 16px;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}
.auth-submit {
  width: 100%;
}
.sent-tip {
  margin-top: 14px;
  font-size: 13px;
  color: var(--el-color-success);
  text-align: center;
}
.auth-footer {
  margin-top: 14px;
  text-align: center;
  font-size: 13px;
}
</style>
