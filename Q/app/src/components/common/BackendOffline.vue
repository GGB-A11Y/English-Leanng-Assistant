<script setup>
import { useBackendStore } from '@/stores/backend'

const backendStore = useBackendStore()
</script>

<template>
  <el-alert
    title="无法连接后端服务"
    description="后端(LangChain 服务)似乎未启动,AI 功能暂时不可用。请确认后端已启动(默认端口 8000)后重试。"
    type="warning"
    show-icon
    :closable="false"
  >
    <template #default>
      <el-button size="small" type="primary" plain :loading="backendStore.online === null" @click="backendStore.checkHealth()">
        TMD
      </el-button>
    </template>
  </el-alert>
</template>
