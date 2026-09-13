<script setup>
import { useIsXs } from '@/composables/useMediaQuery'

// 单词完整词条卡片(契约字段见 docs/API.md:GET /api/vocabulary/words/{id})
const props = defineProps({
  word: { type: Object, required: true },
})

// 窄屏:释义改单列、词根词缀表改卡片
const isXs = useIsXs()

// 用浏览器原生 speechSynthesis 免费朗读,零依赖
function speak() {
  if (!props.word.word) return
  const utterance = new SpeechSynthesisUtterance(props.word.word)
  utterance.lang = 'en-US'
  const voice = speechSynthesis
    .getVoices()
    .find((v) => v.lang.startsWith('en'))
  if (voice) utterance.voice = voice
  speechSynthesis.cancel()
  speechSynthesis.speak(utterance)
}
</script>

<template>
  <el-card class="word-card">
    <div class="head">
      <div class="title-line">
        <span class="word">{{ word.word }}</span>
        <span v-if="word.phonetic" class="phonetic">/{{ word.phonetic }}/</span>
        <el-button v-if="word.phonetic" link type="primary" @click="speak">
          <el-icon><Microphone /></el-icon>朗读
        </el-button>
        <el-tag v-if="word.pos" size="small" class="pos">{{ word.pos }}</el-tag>
      </div>
      <div class="tags">
        <el-tag v-for="t in word.tags || []" :key="t" size="small" type="info" class="tag-item">{{ t }}</el-tag>
      </div>
    </div>

    <el-descriptions :column="isXs ? 1 : 2" border>
      <el-descriptions-item label="中文释义">{{ word.definition_cn || '—' }}</el-descriptions-item>
      <el-descriptions-item label="英文释义">{{ word.definition_en || '—' }}</el-descriptions-item>
    </el-descriptions>

    <template v-if="word.examples?.length">
      <h3 class="section-title">例句</h3>
      <div v-for="(ex, i) in word.examples" :key="i" class="example">
        <div class="ex-sentence">{{ ex.sentence }}</div>
        <div class="ex-translation">{{ ex.translation }}</div>
      </div>
    </template>

    <template v-if="word.roots_affixes?.length">
      <h3 class="section-title">词根词缀</h3>
      <!-- 窄屏卡片化(表格列宽合计约 450px,手机上放不下) -->
      <div v-if="isXs" class="root-cards">
        <div v-for="(r, i) in word.roots_affixes" :key="i" class="root-card">
          <div class="rc-head">
            <span class="rc-part">{{ r.part }}</span>
            <span class="rc-meaning">{{ r.meaning }}</span>
          </div>
          <div v-if="r.words?.length" class="rc-words">
            <el-tag v-for="w in r.words" :key="w" size="small" type="info" class="tag-item">{{ w }}</el-tag>
          </div>
        </div>
      </div>
      <el-table v-else :data="word.roots_affixes" size="small">
        <el-table-column prop="part" label="词根/词缀" width="150" />
        <el-table-column prop="meaning" label="含义" width="180" />
        <el-table-column label="例词">
          <template #default="{ row }">{{ (row.words || []).join(', ') }}</template>
        </el-table-column>
      </el-table>
    </template>

    <template v-if="word.synonyms?.length || word.antonyms?.length">
      <h3 class="section-title">近义词 / 反义词</h3>
      <div class="syn-ant">
        <template v-if="word.synonyms?.length">
          <span class="label">近义</span>
          <el-tag v-for="s in word.synonyms" :key="s" size="small" type="success" class="tag-item">{{ s }}</el-tag>
        </template>
        <template v-if="word.antonyms?.length">
          <span class="label" :style="{ marginLeft: word.synonyms?.length ? '16px' : '0' }">反义</span>
          <el-tag v-for="a in word.antonyms" :key="a" size="small" type="danger" class="tag-item">{{ a }}</el-tag>
        </template>
      </div>
    </template>

    <template v-if="word.collocations?.length">
      <h3 class="section-title">常见搭配</h3>
      <el-tag v-for="c in word.collocations" :key="c" size="small" type="info" class="tag-item">{{ c }}</el-tag>
    </template>

    <div v-if="word.note" class="note">
      <b>我的备注:</b>{{ word.note }}
    </div>
  </el-card>
</template>

<style scoped>
.head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
}
.title-line {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.word {
  font-size: 34px;
  font-weight: 700;
}
.phonetic {
  color: var(--el-text-color-secondary);
  font-size: 16px;
}
.pos {
  align-self: center;
}
.tags {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
.tag-item {
  margin-bottom: 4px;
}
.section-title {
  margin: 20px 0 10px;
  font-size: 15px;
  color: var(--el-text-color-primary);
}
.example {
  margin-bottom: 10px;
  padding-left: 10px;
  border-left: 3px solid var(--el-color-primary-light-5);
}
.ex-sentence {
  font-size: 15px;
}
.ex-translation {
  color: var(--el-text-color-secondary);
  font-size: 13px;
}
.syn-ant {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
}
.label {
  color: var(--el-text-color-secondary);
  font-size: 13px;
}
.note {
  margin-top: 20px;
  padding: 10px 14px;
  background: var(--el-color-warning-light-9);
  border-radius: 6px;
  font-size: 14px;
  color: var(--el-text-color-primary);
}

/* ---- 窄屏词根词缀卡片 ---- */
.root-cards {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.root-card {
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  padding: 10px 12px;
}
.rc-head {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.rc-part {
  font-weight: 600;
  font-size: 15px;
  color: var(--el-color-primary);
}
.rc-meaning {
  font-size: 14px;
  color: var(--el-text-color-regular);
}
.rc-words {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-top: 6px;
}

/* 窄屏:标题区留白收紧 */
@media (max-width: 767px) {
  .word {
    font-size: 28px;
  }
  .head {
    margin-bottom: 12px;
  }
}
</style>
