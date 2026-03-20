<template>
  <div class="mindmap-container">
    <div class="mindmap-header">
      <h2 class="mindmap-title">测试用例思维导图</h2>
      <div class="mindmap-actions">
        <el-button size="small" @click="zoomIn">🔍 放大</el-button>
        <el-button size="small" @click="zoomOut">🔎 缩小</el-button>
        <el-button size="small" @click="fitView">📐 适应屏幕</el-button>
      </div>
    </div>
    <div ref="mindmapRef" class="mindmap-content"></div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { Transformer } from 'markmap-lib'
import { Markmap, loadCSS, loadJS } from 'markmap-view'
import type { IMarkmapOptions } from 'markmap-common'

interface MindMapNode {
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

const mindmapRef = ref<HTMLElement | null>(null)
let markmap: Markmap | null = null
const transformer = new Transformer()

const zoomIn = () => {
  if (markmap) {
    const scale = markmap.state.scale * 1.2
    markmap.setScale(scale)
  }
}

const zoomOut = () => {
  if (markmap) {
    const scale = markmap.state.scale * 0.8
    markmap.setScale(scale)
  }
}

const fitView = () => {
  if (markmap) {
    markmap.fit()
  }
}

const renderMindMap = (data: MindMapNode | null) => {
  if (!data || !mindmapRef.value) return
  
  const markdown = convertToMarkdown(data)
  const { root, features } = transformer.transform(markdown)
  
  const options: IMarkmapOptions = {
    autoFit: true,
    duration: 500,
    paddingX: 50,
    spacingHorizontal: 80,
    spacingVertical: 10,
    maxWidth: 0,
    max_width: 0,
    initialExpandLevel: 2,
    color: (node: any) => {
      const depth = node.depth || 0
      const colors = ['#4f46e5', '#7c3aed', '#db2777', '#ea580c', '#059669']
      return colors[depth % colors.length]
    },
    nodeMinRadius: 10,
    nodeMaxRadius: 30,
  }

  if (markmap) {
    markmap.setData(root)
  } else {
    markmap = Markmap.create(mindmapRef.value, options, root)
  }
  
  if (features.styles?.length) {
    loadCSS(features.styles)
  }
  if (features.scripts?.length) {
    loadJS(features.scripts, { getAsync: true })
  }
}

const convertToMarkdown = (node: MindMapNode, level = 0): string => {
  let markdown = ''
  const prefix = '#'.repeat(level + 1) + ' '
  
  let content = node.content
  if (node.payload) {
    const extras = []
    if (node.payload.priority) extras.push(`【优先级：${node.payload.priority}】`)
    if (node.payload.type) extras.push(`类型：${node.payload.type}`)
    if (node.payload.status) extras.push(`状态：${node.payload.status}`)
    if (node.payload.description) extras.push(node.payload.description)
    
    if (extras.length > 0) {
      content += ` - ${extras.join(' | ')}`
    }
  }
  
  markdown += `${prefix}${content}\n\n`
  
  if (node.children && node.children.length > 0) {
    for (const child of node.children) {
      markdown += convertToMarkdown(child, level + 1)
    }
  }
  
  return markdown
}

watch(() => props.data, (newData) => {
  if (newData) {
    setTimeout(() => renderMindMap(newData), 100)
  }
}, { immediate: true, deep: true })

onMounted(() => {
  if (props.data) {
    renderMindMap(props.data)
  }
})
</script>

<style scoped>
.mindmap-container {
  width: 100%;
  height: 100%;
  background: #ffffff;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.mindmap-header {
  padding: 16px 24px;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
}

.mindmap-title {
  font-size: 18px;
  font-weight: 700;
  color: #1e293b;
  margin: 0;
}

.mindmap-actions {
  display: flex;
  gap: 8px;
}

.mindmap-content {
  flex: 1;
  min-height: 500px;
  position: relative;
}

:deep(.markmap) {
  width: 100%;
  height: 100%;
}

:deep(.markmap-node) {
  cursor: pointer;
}

:deep(.markmap-node:hover > .markmap-foreign-object) {
  filter: brightness(0.95);
}

:deep(.markmap-foreign-object) {
  transition: all 0.2s ease;
}

:deep(.markmap-foreign-object rect) {
  rx: 8;
  ry: 8;
  stroke-width: 2;
}

:deep(.markmap-link) {
  stroke-width: 2;
}
</style>
