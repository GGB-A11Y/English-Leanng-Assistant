<script setup>
import { computed } from 'vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'

// AI 输出为 markdown,渲染前经 DOMPurify 清洗防 XSS(样式见 main.css 的 .markdown-body)
const props = defineProps({
  content: { type: String, default: '' },
})

const html = computed(() => DOMPurify.sanitize(marked.parse(props.content ?? '')))
</script>

<template>
  <div class="markdown-body" v-html="html"></div>
</template>
