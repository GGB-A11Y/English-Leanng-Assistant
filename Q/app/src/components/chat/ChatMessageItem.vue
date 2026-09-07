<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import MarkdownBlock from '@/components/common/MarkdownBlock.vue'
import { translateApi } from '@/api/translate'
import { formatDateTime } from '@/utils/format'

// message: { id, role: 'user'|'assistant', content, created_at, streaming?, interrupted?, error? }
// streamingContent: 该消息正在流式生成时的增量内容(仅对 streaming 消息传入)
const props = defineProps({
  message: { type: Object, required: true },
  streamingContent: { type: String, default: '' },
})

async function copyContent() {
  try {
    await navigator.clipboard.writeText(props.message.content)
    ElMessage.success('已复制')
  } catch {
    ElMessage.error('复制失败')
  }
}

// AI 回复的中英互译:默认不展示,点「翻译」按钮才按需调用(结果缓存,再次点击收起)
const showTranslation = ref(false)
const translating = ref(false)
const translationText = ref('')

function hasCJK(text) {
  return /[一-鿿]/.test(text)
}

async function toggleTranslation() {
  if (showTranslation.value) {
    showTranslation.value = false
    return
  }
  if (translationText.value) {
    showTranslation.value = true
    return
  }
  translating.value = true
  try {
    const text = props.message.content
    // 后端翻译接口限 2000 字符(契约 3.4),长消息先提示,避免必然 422
    if (text.length > 2000) {
      ElMessage.warning('消息过长(超过 2000 字符),请分段复制后到翻译页翻译')
      return
    }
    const isZh = hasCJK(text)
    const data = await translateApi.translate({
      text,
      source_lang: isZh ? 'zh' : 'en',
      target_lang: isZh ? 'en' : 'zh',
    })
    translationText.value = data.translation
    showTranslation.value = true
  } catch {
    // 错误已由 request.js 统一提示
  } finally {
    translating.value = false
  }
}
</script>

<template>
  <div class="msg-row" :class="message.role">
    <el-avatar v-if="message.role === 'assistant'" :size="36" class="avatar">AI</el-avatar>

    <div class="bubble-wrap">
      <div class="bubble" :class="{ 'bubble-user': message.role === 'user' }">
        <template v-if="message.role === 'user'">
          <div class="user-text">{{ message.content }}</div>
        </template>
        <template v-else>
          <MarkdownBlock v-if="message.content || streamingContent" :content="message.content + streamingContent" />
          <div v-else-if="message.streaming" class="thinking">
            <el-icon class="is-loading"><Loading /></el-icon>
            正在思考…
          </div>
          <div v-if="message.interrupted" class="msg-note">已停止生成,以上为部分内容</div>
          <div v-if="message.error" class="msg-note error">生成失败</div>
        </template>
      </div>
      <div class="msg-meta">
        <span>{{ formatDateTime(message.created_at) }}</span>
        <el-button
          v-if="message.content && !message.streaming"
          link
          size="small"
          type="info"
          @click="copyContent"
        >
          <el-icon><CopyDocument /></el-icon>复制
        </el-button>
        <el-button
          v-if="message.role === 'assistant' && message.content && !message.streaming"
          link
          size="small"
          type="info"
          :loading="translating"
          @click="toggleTranslation"
        >
          <el-icon><Connection /></el-icon>{{ showTranslation ? '收起翻译' : '翻译' }}
        </el-button>
      </div>

      <div v-if="showTranslation && translationText" class="translation-box">
        {{ translationText }}
      </div>
    </div>

    <el-avatar v-if="message.role === 'user'" :size="36" class="avatar avatar-user">我</el-avatar>
  </div>
</template>

<style scoped>
.msg-row {
  display: flex;
  gap: 10px;
  margin-bottom: 16px;
}
.msg-row.user {
  flex-direction: row-reverse;
}
.avatar {
  flex-shrink: 0;
  font-size: 12px;
}
.avatar-user {
  background: var(--el-color-primary);
}
.bubble-wrap {
  max-width: 76%;
  display: flex;
  flex-direction: column;
}
.msg-row.user .bubble-wrap {
  align-items: flex-end;
}
.bubble {
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 10px;
  padding: 10px 14px;
  line-height: 1.6;
}
.bubble-user {
  background: var(--el-color-primary);
  border-color: var(--el-color-primary);
  color: #fff;
}
.user-text {
  white-space: pre-wrap;
  word-break: break-word;
}
.thinking {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}
.msg-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-top: 4px;
}
.translation-box {
  margin-top: 6px;
  padding: 8px 12px;
  border-left: 3px solid var(--el-color-success);
  background: var(--el-color-success-light-9);
  border-radius: 6px;
  font-size: 13px;
  color: var(--el-text-color-regular);
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}
.msg-note {
  margin-top: 8px;
  font-size: 12px;
  color: var(--el-color-warning);
}
.msg-note.error {
  color: var(--el-color-danger);
}
</style>
