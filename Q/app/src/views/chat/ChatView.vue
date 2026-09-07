<script setup>
import { ref, computed, watch, nextTick, onMounted } from 'vue'
import { useChatStore } from '@/stores/chat'
import { useBackendStore } from '@/stores/backend'
import ChatMessageItem from '@/components/chat/ChatMessageItem.vue'

const store = useChatStore()
const backendStore = useBackendStore()

const input = ref('')
const listRef = ref(null)

onMounted(async () => {
  await store.fetchSessions().catch(() => {})
  // 恢复上次打开的会话(store 持久化了 currentSessionId)
  const saved = store.currentSessionId
  if (saved && store.sessions.some((s) => s.id === saved)) {
    store.selectSession(saved)
  }
})

const messages = computed(() => store.messages)

async function createSession() {
  try {
    await store.createSession()
  } catch {
    // 错误已提示
  }
}

async function send() {
  const content = input.value.trim()
  if (!content) return
  // 只有消息被真正接受(已推入列表)才清空输入,避免后端不可用/生成中时输入被吞
  const ok = await store.sendMessage(content)
  if (ok) input.value = ''
}

function onKeydown(e) {
  // Enter 发送,Shift+Enter 换行
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    send()
  }
}

// 消息变化时自动滚到底部
watch(
  () => [store.messages.length, store.streamingContent],
  async () => {
    await nextTick()
    const el = listRef.value
    if (el) el.scrollTop = el.scrollHeight
  },
)
</script>

<template>
  <div class="chat-view">
    <div class="session-panel">
      <el-button
        type="primary"
        class="new-btn"
        :disabled="backendStore.online === false || store.streaming"
        @click="createSession"
      >
        <el-icon><Plus /></el-icon>新建对话
      </el-button>
      <el-scrollbar class="session-list">
        <div
          v-for="s in store.sessions"
          :key="s.id"
          class="session-item"
          :class="{ active: s.id === store.currentSessionId }"
          @click="store.selectSession(s.id)"
        >
          <div class="session-main">
            <div class="session-title">{{ s.title || '新对话' }}</div>
            <div class="session-meta">{{ s.message_count ?? 0 }} 条消息</div>
          </div>
          <el-popconfirm title="删除该对话?" @confirm="store.deleteSession(s.id)">
            <template #reference>
              <el-button link class="session-del" :disabled="store.streaming" @click.stop>
                <el-icon><Delete /></el-icon>
              </el-button>
            </template>
          </el-popconfirm>
        </div>
        <el-empty v-if="!store.sessions.length" description="还没有对话" :image-size="70" />
      </el-scrollbar>
    </div>

    <div class="chat-panel">
      <div ref="listRef" class="message-list">
        <el-empty
          v-if="!messages.length"
          description="点击左侧「新建对话」,和 AI 教练开始英语对话练习吧"
        >
          <template #default>
            <div class="empty-tips">
              <div>AI 教练会:</div>
              <div>· 全程用英语和你交流</div>
              <div>· 纠正你的语法错误并给出更地道的表达</div>
            </div>
          </template>
        </el-empty>
        <ChatMessageItem
          v-for="m in messages"
          :key="m.id"
          :message="m"
          :streaming-content="store.streaming && m.streaming ? store.streamingContent : ''"
        />
      </div>

      <div class="input-area">
        <el-input
          v-model="input"
          type="textarea"
          :autosize="{ minRows: 2, maxRows: 6 }"
          placeholder="用英语输入你想说的话,如:I go to park yesterday. (Enter 发送,Shift+Enter 换行)"
          :disabled="backendStore.online === false"
          @keydown="onKeydown"
        />
        <div class="input-actions">
          <span v-if="backendStore.online === false" class="offline-note">后端离线,无法发送消息</span>
          <el-button
            v-if="!store.streaming"
            type="primary"
            :loading="store.sending"
            :disabled="!input.trim() || backendStore.online === false"
            @click="send"
          >
            发送
          </el-button>
          <el-button v-else type="danger" @click="store.stopStreaming()">
            <el-icon><VideoPause /></el-icon>停止生成
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.chat-view {
  display: flex;
  gap: 16px;
  height: calc(100vh - 120px);
  min-height: 480px;
}
.session-panel {
  width: 240px;
  flex-shrink: 0;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  background: var(--el-bg-color);
  display: flex;
  flex-direction: column;
  padding: 12px;
}
.new-btn {
  margin-bottom: 12px;
}
.session-list {
  flex: 1;
}
.session-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px;
  border-radius: 6px;
  cursor: pointer;
  margin-bottom: 4px;
}
.session-item:hover {
  background: var(--el-fill-color-light);
}
.session-item.active {
  background: var(--el-color-primary-light-9);
}
.session-main {
  min-width: 0;
}
.session-title {
  font-size: 14px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.session-meta {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
.session-del {
  opacity: 0;
  transition: opacity 0.2s;
}
.session-item:hover .session-del {
  opacity: 1;
}
.chat-panel {
  flex: 1;
  min-width: 0;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  background: var(--el-bg-color);
  display: flex;
  flex-direction: column;
}
.message-list {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}
.empty-tips {
  font-size: 13px;
  color: var(--el-text-color-secondary);
  line-height: 1.9;
}
.input-area {
  border-top: 1px solid var(--el-border-color-lighter);
  padding: 14px;
}
.input-actions {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 12px;
  margin-top: 10px;
}
.offline-note {
  font-size: 13px;
  color: var(--el-color-danger);
}
</style>
