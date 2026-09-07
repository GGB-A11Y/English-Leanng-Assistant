<script setup>
import { ref, computed, watch } from 'vue'
import MarkdownBlock from '@/components/common/MarkdownBlock.vue'
import { writingApi } from '@/api/writing'
import { CORRECTION_TYPES } from '@/constants'
import { scoreColor } from '@/utils/format'

// 批改结果面板:评分环 + tabs(总评/优缺点/逐句纠错/词汇建议/范文)
const props = defineProps({
  result: { type: Object, required: true }, // { score, level, feedback: {...} }
  topicId: { type: String, default: '' },
})

// 面板在结果页切换记录时不卸载,props 会变,须用 computed 保持响应式
const scorePercent = computed(() => Math.round(props.result?.score ?? 0))
const feedback = computed(() => props.result?.feedback || {})

const activeNames = ref([])
const sampleLoading = ref(false)
const sample = ref(null)
const sampleError = ref(false)

// 切换作文时重置范文缓存与折叠状态,避免串题(展开看到上一篇的范文)
watch(
  () => props.result,
  () => {
    sample.value = null
    sampleError.value = false
    activeNames.value = []
  },
)

// 首次展开"参考范文"时按需生成
async function loadSample() {
  if (sample.value || sampleLoading.value || !props.topicId) return
  sampleLoading.value = true
  sampleError.value = false
  try {
    const data = await writingApi.generateSample(props.topicId)
    sample.value = data.essay
  } catch {
    sampleError.value = true
  } finally {
    sampleLoading.value = false
  }
}

function correctionTypeLabel(type) {
  return CORRECTION_TYPES[type] || type || '—'
}
</script>

<template>
  <div class="result-panel">
    <div class="score-header">
      <el-progress
        type="circle"
        :percentage="scorePercent"
        :width="120"
        :color="scoreColor(scorePercent / 100)"
      >
        <template #default>
          <div class="score-num">{{ result.score }}</div>
          <div class="score-label">总分</div>
        </template>
      </el-progress>
      <el-tag v-if="result.level" size="large" type="primary">{{ result.level }} 水平</el-tag>
    </div>

    <el-tabs>
      <el-tab-pane label="总评">
        <MarkdownBlock v-if="feedback.overall_comment" :content="feedback.overall_comment" />
        <el-empty v-else description="暂无总评" :image-size="60" />
      </el-tab-pane>

      <el-tab-pane label="优点与不足">
        <div class="two-col">
          <div class="col-card">
            <h4 class="col-title good">优点</h4>
            <ul v-if="feedback.strengths?.length">
              <li v-for="(s, i) in feedback.strengths" :key="i">{{ s }}</li>
            </ul>
            <el-empty v-else description="暂无" :image-size="50" />
          </div>
          <div class="col-card">
            <h4 class="col-title bad">不足</h4>
            <ul v-if="feedback.weaknesses?.length">
              <li v-for="(w, i) in feedback.weaknesses" :key="i">{{ w }}</li>
            </ul>
            <el-empty v-else description="暂无" :image-size="50" />
          </div>
        </div>
      </el-tab-pane>

      <el-tab-pane label="逐句纠错">
        <el-table v-if="feedback.corrections?.length" :data="feedback.corrections" size="small">
          <el-table-column prop="original" label="原句" min-width="200" />
          <el-table-column prop="corrected" label="修改建议" min-width="200" />
          <el-table-column label="错误类型" width="110">
            <template #default="{ row }">
              <el-tag size="small" type="warning">{{ correctionTypeLabel(row.type) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="explanation" label="说明" min-width="180" />
        </el-table>
        <el-empty v-else description="没有发现明显错误,写得很棒!" :image-size="60" />
      </el-tab-pane>

      <el-tab-pane label="词汇建议">
        <el-table v-if="feedback.vocabulary_suggestions?.length" :data="feedback.vocabulary_suggestions" size="small">
          <el-table-column prop="original" label="原词" width="160" />
          <el-table-column prop="suggestion" label="建议替换" width="160" />
          <el-table-column prop="reason" label="理由" min-width="200" />
        </el-table>
        <el-empty v-else description="暂无词汇建议" :image-size="60" />
      </el-tab-pane>

      <el-tab-pane label="参考范文">
        <el-collapse v-model="activeNames" @change="loadSample">
          <el-collapse-item name="sample">
            <template #title>
              <span>展开查看参考范文</span>
              <el-tag v-if="!topicId" size="small" type="info" style="margin-left: 8px">需选择题目后生成</el-tag>
            </template>
            <el-skeleton v-if="sampleLoading" :rows="6" animated />
            <el-alert v-else-if="sampleError" title="范文生成失败,请重试" type="error" :closable="false" />
            <MarkdownBlock v-else-if="sample" :content="sample" />
            <el-empty v-else description="展开后自动生成参考范文" :image-size="50" />
          </el-collapse-item>
        </el-collapse>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<style scoped>
.score-header {
  display: flex;
  align-items: center;
  gap: 24px;
  margin-bottom: 16px;
}
.score-num {
  font-size: 26px;
  font-weight: 700;
}
.score-label {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
.two-col {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}
.col-card {
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  padding: 14px;
}
.col-title {
  margin: 0 0 10px;
}
.col-title.good {
  color: var(--el-color-success);
}
.col-title.bad {
  color: var(--el-color-danger);
}
.col-card ul {
  padding-left: 1.4em;
  margin: 0;
  line-height: 1.8;
}
</style>
