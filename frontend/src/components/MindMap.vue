<template>
  <div class="mindmap-wrapper">
    <div class="mindmap-toolbar">
      <el-button size="small" @click="zoomIn">🔍 放大</el-button>
      <el-button size="small" @click="zoomOut">🔎 缩小</el-button>
      <el-button size="small" @click="fit">适应屏幕</el-button>
      <el-button size="small" @click="exportXmind">📥 导出 XMind</el-button>
    </div>
    <div ref="mindmapContainer" class="mindmap-container"></div>
  </div>
</template>

<script setup lang="ts">
import { ref, onUnmounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import MindMap from 'simple-mind-map'

export interface MindMapNode {
  content: string
  children?: MindMapNode[]
  payload?: {
    id?: string
    type?: string
    priority?: string
    description?: string
    status?: string
  }
}

const props = defineProps<{
  data: MindMapNode | null
}>()

const mindmapContainer = ref<HTMLElement | null>(null)
let mindMapInstance: any = null

// 转换数据格式
const convertData = (node: MindMapNode): any => {
  return {
    data: {
      text: node.content,
      ...node.payload
    },
    children: node.children ? node.children.map(child => convertData(child)) : []
  }
}

// 初始化思维导图
const initMindMap = () => {
  if (!props.data || !mindmapContainer.value) return
  
  // 销毁旧实例
  if (mindMapInstance) {
    mindMapInstance.destroy()
  }
  
  // 创建新实例
  try {
    mindMapInstance = new (MindMap as any)({
      el: mindmapContainer.value,
      data: convertData(props.data),
      theme: 'avocado',
      layout: 'logicalStructure',
      fit: true,
    })
    
    console.log('[MindMap] 实例创建成功')
  } catch (error) {
    console.error('[MindMap] 实例创建失败:', error)
    ElMessage.error('思维导图加载失败')
  }
}

// 放大
const zoomIn = () => {
  if (!mindMapInstance) {
    ElMessage.warning('思维导图还未加载')
    return
  }
  const scale = mindMapInstance.view.getScale()
  mindMapInstance.view.setTransform(null, null, scale + 0.2)
  ElMessage.success('已放大')
}

// 缩小
const zoomOut = () => {
  if (!mindMapInstance) {
    ElMessage.warning('思维导图还未加载')
    return
  }
  const scale = mindMapInstance.view.getScale()
  const newScale = Math.max(0.1, scale - 0.2)
  mindMapInstance.view.setTransform(null, null, newScale)
  ElMessage.success('已缩小')
}

// 适应屏幕
const fit = () => {
  if (!mindMapInstance) {
    ElMessage.warning('思维导图还未加载')
    return
  }
  mindMapInstance.fit()
  ElMessage.success('已适应屏幕')
}

// 导出 XMind
const exportXmind = () => {
  if (!mindMapInstance) {
    ElMessage.warning('思维导图还未加载')
    return
  }
  try {
    ElMessage.info('正在生成 XMind 文件...')
    mindMapInstance.export('xmind', '测试用例')
    ElMessage.success('XMind 文件已生成')
  } catch (error) {
    console.error('导出失败:', error)
    ElMessage.error('导出 XMind 失败')
  }
}

// 监听数据变化
watch(() => props.data, (newData) => {
  console.log('[MindMap] 数据变化:', newData ? '有数据' : '无数据')
  if (newData && mindmapContainer.value) {
    // 等待 DOM 更新后再初始化
    setTimeout(() => {
      initMindMap()
    }, 100)
  }
}, { immediate: false })

// 组件挂载时如果有数据则初始化
watch(
  () => ({ data: props.data, container: mindmapContainer.value }),
  ({ data, container }) => {
    if (data && container && !mindMapInstance) {
      setTimeout(() => {
        initMindMap()
      }, 200)
    }
  },
  { immediate: true }
)

// 组件卸载时清理
onUnmounted(() => {
  if (mindMapInstance) {
    mindMapInstance.destroy()
    mindMapInstance = null
  }
})
</script>

<style scoped>
.mindmap-wrapper {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.mindmap-toolbar {
  padding: 12px;
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.mindmap-container {
  flex: 1;
  width: 100%;
  min-height: 600px;
  background: #ffffff;
  overflow: hidden;
}
</style>
