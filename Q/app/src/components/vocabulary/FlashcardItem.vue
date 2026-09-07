<script setup>
import { ref, watch, onMounted, onUnmounted } from 'vue'
import { REVIEW_GRADES } from '@/constants'

// 3D 翻转闪卡:正面单词 → 点击/空格翻面 → 四档评分(键盘 1-4)
const props = defineProps({
  word: { type: Object, required: true },
})
const emit = defineEmits(['rated'])

const flipped = ref(false)
const rated = ref(false)

// 切换单词时重置卡片
watch(
  () => props.word,
  () => {
    flipped.value = false
    rated.value = false
  },
)

function flip() {
  if (!rated.value) flipped.value = !flipped.value
}

function rate(quality) {
  if (rated.value) return
  rated.value = true
  emit('rated', quality)
}

function onKeydown(e) {
  if (e.code === 'Space') {
    e.preventDefault()
    flip()
    return
  }
  const keyMap = { Digit1: 0, Digit2: 2, Digit3: 4, Digit4: 5 }
  if (flipped.value && keyMap[e.code] !== undefined) {
    rate(keyMap[e.code])
  }
}

onMounted(() => window.addEventListener('keydown', onKeydown))
onUnmounted(() => window.removeEventListener('keydown', onKeydown))
</script>

<template>
  <div class="flashcard-wrap">
    <div class="flashcard" :class="{ flipped }" @click="flip">
      <div class="card-inner">
        <div class="card-face front">
          <div class="fc-word">{{ word.word }}</div>
          <div v-if="word.phonetic" class="fc-phonetic">/{{ word.phonetic }}/</div>
          <div class="fc-hint">点击卡片或按空格键查看释义</div>
        </div>
        <div class="card-face back">
          <div class="fc-word">{{ word.word }}</div>
          <div class="fc-definition">{{ word.definition_cn || '—' }}</div>
          <div v-if="word.examples?.length" class="fc-examples">
            <div v-for="(ex, i) in word.examples.slice(0, 2)" :key="i" class="fc-example">
              <b>{{ ex.sentence }}</b>
              <div class="fc-example-trans">{{ ex.translation }}</div>
            </div>
          </div>
          <div class="fc-familiarity">熟悉度 {{ word.familiarity ?? 0 }}/5</div>
        </div>
      </div>
    </div>

    <div v-if="flipped && !rated" class="grades">
      <span class="grades-label">这个单词你记得怎么样?</span>
      <div class="grades-btns">
        <el-button
          v-for="(g, i) in REVIEW_GRADES"
          :key="g.quality"
          :type="g.type"
          @click="rate(g.quality)"
        >
          {{ g.label }}<span class="grade-hint">{{ g.hint }}</span>
          <span class="grade-key">{{ i + 1 }}</span>
        </el-button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.flashcard-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 24px;
  padding: 24px 0;
}
.flashcard {
  width: 420px;
  max-width: 100%;
  height: 260px;
  perspective: 1200px;
  cursor: pointer;
}
.card-inner {
  position: relative;
  width: 100%;
  height: 100%;
  transform-style: preserve-3d;
  transition: transform 0.4s;
}
.flashcard.flipped .card-inner {
  transform: rotateY(180deg);
}
.card-face {
  position: absolute;
  inset: 0;
  backface-visibility: hidden;
  border-radius: 14px;
  border: 1px solid var(--el-border-color-lighter);
  background: var(--el-bg-color);
  box-shadow: var(--el-box-shadow-light);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 24px;
  text-align: center;
}
.card-face.back {
  transform: rotateY(180deg);
}
.fc-word {
  font-size: 40px;
  font-weight: 700;
}
.card-face.back .fc-word {
  font-size: 24px;
}
.fc-phonetic {
  color: var(--el-text-color-secondary);
  font-size: 17px;
}
.fc-hint {
  position: absolute;
  bottom: 14px;
  font-size: 12px;
  color: var(--el-text-color-placeholder);
}
.fc-definition {
  font-size: 18px;
  color: var(--el-color-primary);
}
.fc-examples {
  display: flex;
  flex-direction: column;
  gap: 8px;
  font-size: 14px;
  max-width: 90%;
}
.fc-example-trans {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}
.fc-familiarity {
  position: absolute;
  bottom: 14px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
.grades {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}
.grades-label {
  color: var(--el-text-color-secondary);
  font-size: 13px;
}
.grades-btns {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  justify-content: center;
}
.grade-hint {
  display: block;
  font-size: 11px;
  opacity: 0.8;
}
.grade-key {
  display: block;
  font-size: 11px;
  opacity: 0.7;
}
</style>
