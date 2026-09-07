// 全局枚举与常量(与 docs/API.md 契约保持一致)

// CEFR 难度等级
export const CEFR_LEVELS = [
  { value: 'A1', label: 'A1 入门' },
  { value: 'A2', label: 'A2 基础' },
  { value: 'B1', label: 'B1 中级' },
  { value: 'B2', label: 'B2 中高级' },
  { value: 'C1', label: 'C1 高级' },
]

// SM-2 复习评分档位:quality 值 → 按钮文案与间隔提示(间隔仅为展示,实际由后端算法决定)
export const REVIEW_GRADES = [
  { quality: 0, label: '忘记', hint: '很快再见', type: 'danger' },
  { quality: 2, label: '困难', hint: '间隔缩短', type: 'warning' },
  { quality: 4, label: '良好', hint: '间隔延长', type: 'primary' },
  { quality: 5, label: '简单', hint: '间隔大幅延长', type: 'success' },
]

// 作文纠错类型 → 中文标签
export const CORRECTION_TYPES = {
  grammar: '语法错误',
  word_choice: '用词不当',
  spelling: '拼写错误',
}

// 翻译语言方向
export const TRANSLATE_DIRECTIONS = [
  { value: 'zh2en', label: '中 → 英' },
  { value: 'en2zh', label: '英 → 中' },
]

// 阅读理解的学段分类(后端映射到 CEFR 难度带:小学→A1~A2,初中→A2~B1,高中→B1~B2)
export const READING_STAGES = [
  { value: 'primary', label: '小学', hint: '约100~150词' },
  { value: 'junior', label: '初中', hint: '约200~280词' },
  { value: 'senior', label: '高中', hint: '约300~400词' },
]

// 作文学习的学段分类(题库按 CEFR 映射:小学→A1~A2,初中→B1,高中→B2~C1)
export const WRITING_STAGES = [
  { value: 'primary', label: '小学', hint: 'A1~A2' },
  { value: 'junior', label: '初中', hint: 'B1' },
  { value: 'senior', label: '高中', hint: 'B2~C1' },
]
