<template>
  <div class="mindmap-wrapper">
    <div class="mindmap-toolbar">
      <el-button size="small" @click="zoomIn">🔍 放大</el-button>
      <el-button size="small" @click="zoomOut">🔎 缩小</el-button>
      <el-button size="small" @click="fit">适应屏幕</el-button>
      <el-button size="small" @click="resetView">重置视图</el-button>
      <el-button size="small" @click="exportXmind">📥 导出 XMind</el-button>
    </div>
    <div ref="mindmapContainer" class="mindmap-container"></div>
  </div>
</template>

<script setup lang="ts">
import { ref, onUnmounted, watch, onMounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import MindMap from 'simple-mind-map/full'
import 'simple-mind-map/dist/simpleMindMap.esm.css'

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

const convertData = (node: MindMapNode): any => {
  return {
    data: {
      text: node.content,
      ...node.payload
    },
    children: node.children ? node.children.map(child => convertData(child)) : []
  }
}

const initMindMap = () => {
  if (!props.data) return
  if (!mindmapContainer.value) return
  
  const container = mindmapContainer.value
  if (container.offsetWidth === 0 || container.offsetHeight === 0) {
    setTimeout(() => initMindMap(), 300)
    return
  }
  
  if (mindMapInstance) {
    mindMapInstance.destroy()
    mindMapInstance = null
  }
  
  try {
    mindMapInstance = new (MindMap as any)({
      el: container,
      data: convertData(props.data),
      theme: 'avocado',
      layout: 'logicalStructure',
    })
    
    nextTick(() => {
      if (mindMapInstance?.view) {
        mindMapInstance.view.fit()
      }
    })
  } catch (error) {
    console.error('[MindMap] 创建失败:', error)
    ElMessage.error('思维导图加载失败: ' + (error as Error).message)
  }
}

const zoomIn = () => {
  if (!mindMapInstance) {
    ElMessage.warning('思维导图还未加载')
    return
  }
  mindMapInstance.view.enlarge()
}

const zoomOut = () => {
  if (!mindMapInstance) {
    ElMessage.warning('思维导图还未加载')
    return
  }
  mindMapInstance.view.narrow()
}

const fit = () => {
  if (!mindMapInstance) {
    ElMessage.warning('思维导图还未加载')
    return
  }
  mindMapInstance.view.fit()
}

const resetView = () => {
  if (!mindMapInstance) {
    ElMessage.warning('思维导图还未加载')
    return
  }
  mindMapInstance.view.reset()
}

const exportXmind = async () => {
  if (!mindMapInstance) {
    ElMessage.warning('思维导图还未加载')
    return
  }
  try {
    if (!mindMapInstance.doExportXMind) {
      ElMessage.error('导出插件未注册')
      return
    }
    ElMessage.info('正在生成 XMind 文件...')
    const blob = await mindMapInstance.export('xmind', '测试用例')
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = '测试用例.xmind'
    a.click()
    URL.revokeObjectURL(url)
    ElMessage.success('XMind 文件已生成')
  } catch (error) {
    console.error('导出失败:', error)
    ElMessage.error('导出 XMind 失败: ' + (error as Error).message)
  }
}

watch(() => props.data, async (newData) => {
  if (newData) {
    await nextTick()
    setTimeout(() => initMindMap(), 100)
  }
}, { immediate: false })

onMounted(() => {
  if (props.data) {
    setTimeout(() => initMindMap(), 200)
  }
})

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
  height: 800px;
  display: flex;
  flex-direction: column;
  background: #ffffff;
}

.mindmap-toolbar {
  padding: 12px;
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  flex-shrink: 0;
}

.mindmap-container {
  flex: 1;
  width: 100%;
  min-height: 600px;
  background: #ffffff;
  overflow: hidden;
}
</style>
