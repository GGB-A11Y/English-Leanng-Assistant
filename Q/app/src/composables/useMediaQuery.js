import { ref, onMounted, onUnmounted } from 'vue'

// 响应式媒体查询(供「表格↔卡片」等需要 DOM 切换的判断使用)。
//
// 断点体系(与 main.css 中的 @media 字面量人工同步,两处互相引用本注释):
//   xs <768px / sm 768~991px / md 992~1199px / lg 1200~1599px / xl ≥1600px
// 纯样式适配直接用 @media;只有改 DOM 结构(卡片化、el-descriptions 列数、
// el-steps simple 模式)时才引入本函数。
export function useMediaQuery(query) {
  const matches = ref(false)

  onMounted(() => {
    if (typeof window.matchMedia === 'function') {
      const mql = window.matchMedia(query)
      const onChange = () => {
        matches.value = mql.matches
      }
      if (mql.addEventListener) {
        mql.addEventListener('change', onChange)
        onUnmounted(() => mql.removeEventListener('change', onChange))
      } else if (mql.addListener) {
        // 老 Safari 兼容
        mql.addListener(onChange)
        onUnmounted(() => mql.removeListener(onChange))
      }
      matches.value = mql.matches
    } else {
      // 不支持 matchMedia 的极老浏览器:退化为窗口 resize 粗粒度判断
      const onResize = () => {
        matches.value = window.innerWidth <= 767
      }
      window.addEventListener('resize', onResize)
      onUnmounted(() => window.removeEventListener('resize', onResize))
      onResize()
    }
  })

  return matches
}

// 窄屏(手机):<768px,表格卡片化、steps simple 等场景用
export const useIsXs = () => useMediaQuery('(max-width: 767px)')
