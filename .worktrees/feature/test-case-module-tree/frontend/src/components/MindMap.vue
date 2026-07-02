<template>
  <div class="mindmap-wrapper">
    <div class="mindmap-toolbar">
      <template v-if="editable">
        <el-button size="small" type="primary" color="#4f46e5" @click="addChild">
          <el-icon class="mr-1"><Plus /></el-icon>子节点
        </el-button>
        <el-button size="small" @click="addSibling">同级节点</el-button>
        <el-button size="small" type="danger" plain @click="removeNode">删除</el-button>
        <el-divider direction="vertical" />
        <el-button size="small" @click="undo" :disabled="!canUndo" title="撤销 (Ctrl+Z)">
          <el-icon class="mr-1"><Back /></el-icon>撤销
        </el-button>
        <el-button size="small" @click="redo" :disabled="!canRedo" title="重做 (Ctrl+Y)">
          <el-icon class="mr-1"><Right /></el-icon>重做
        </el-button>
        <el-divider direction="vertical" />
        <el-button size="small" type="success" @click="handleSave" :loading="saving">
          <el-icon class="mr-1"><Check /></el-icon>保存
        </el-button>
        <span v-if="hasUnsavedChanges" class="text-xs text-orange-500 ml-1">● 未保存</span>
        <el-divider direction="vertical" />
      </template>
      <el-button size="small" @click="zoomIn">放大</el-button>
      <el-button size="small" @click="zoomOut">缩小</el-button>
      <el-button size="small" @click="fit">适应</el-button>
      <el-button size="small" @click="resetView">重置</el-button>
      <el-button size="small" @click="exportXmind">导出 XMind</el-button>
      <template v-if="editable">
        <span class="ml-auto text-xs text-gray-400 hidden sm:inline">
          双击编辑 | Tab 子节点 | Enter 同级 | Delete 删除 | Ctrl+Z 撤销 | Ctrl+Y 重做
        </span>
      </template>
    </div>
    <div ref="mindmapContainer" class="mindmap-container"></div>
  </div>
</template>

<script setup lang="ts">
import { ref, onUnmounted, watch, onMounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus, Check, Back, Right } from '@element-plus/icons-vue'
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
    color?: string
  }
}

const props = withDefaults(defineProps<{
  data: MindMapNode | null
  editable?: boolean
}>(), {
  editable: false,
})

const emit = defineEmits<{
  (e: 'save', data: MindMapNode): void
  (e: 'node-click', data: MindMapNode): void
}>()

const mindmapContainer = ref<HTMLElement | null>(null)
const canUndo = ref(false)
const canRedo = ref(false)
const saving = ref(false)
const hasUnsavedChanges = ref(false)
let mindMapInstance: any = null

const convertData = (node: MindMapNode): any => {
  const result: any = {
    data: {
      text: node.content,
      ...node.payload
    },
    children: node.children ? node.children.map(child => convertData(child)) : []
  }

  if (node.payload?.type === 'execution-result' && node.payload.color) {
    result.data.borderColor = node.payload.color
    result.data.borderWidth = 2
  }

  return result
}

const convertBack = (node: any): MindMapNode => {
  const { text, id, type, priority, description, status, color } = node.data || {}
  return {
    content: text || '',
    children: node.children ? node.children.map((child: any) => convertBack(child)) : [],
    payload: { id, type, priority, description, status, color },
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
      readonly: !props.editable,
      enableShortcutOnlyWhenMouseInSvg: true,
      nodeTextEditZIndex: 1000,
      textAutoWrapWidth: 300,
      maxHistoryCount: 500,
      isUseCustomNodeContent: false,
      customHandleClipboardText: null,
    })

    if (props.editable) {
      mindMapInstance.on('back_forward', (index: any, len: any) => {
        if (typeof index === 'object') {
          canUndo.value = (index.index ?? 0) > 0
          canRedo.value = (index.index ?? 0) < (index.len ?? 1) - 1
        } else {
          canUndo.value = index > 0
          canRedo.value = index < len - 1
        }
      })
      mindMapInstance.on('data_change', () => {
        hasUnsavedChanges.value = true
      })
    }

    mindMapInstance.on('node_click', (node: any) => {
      emit('node-click', convertBack(node.nodeData || { data: node.getData?.() || {} }))
    })

    mindMapInstance.on('ready', () => {
      if (mindMapInstance?.view) {
        mindMapInstance.view.fit()
      }
    })
  } catch (error) {
    console.error('[MindMap] 创建失败:', error)
    ElMessage.error('思维导图加载失败: ' + (error as Error).message)
  }
}

const addChild = () => {
  if (!mindMapInstance) return
  mindMapInstance.execCommand('INSERT_CHILD_NODE')
}

const addSibling = () => {
  if (!mindMapInstance) return
  mindMapInstance.execCommand('INSERT_NODE')
}

const removeNode = () => {
  if (!mindMapInstance) return
  mindMapInstance.execCommand('REMOVE_NODE')
}

const undo = () => {
  if (!mindMapInstance) return
  mindMapInstance.execCommand('BACK')
}

const redo = () => {
  if (!mindMapInstance) return
  mindMapInstance.execCommand('FORWARD')
}

const handleSave = () => {
  if (!mindMapInstance) return
  saving.value = true
  const rawData = mindMapInstance.getData()
  const converted = convertBack(rawData)
  emit('save', converted)
  hasUnsavedChanges.value = false
  setTimeout(() => { saving.value = false }, 500)
}

const zoomIn = () => {
  if (!mindMapInstance) { ElMessage.warning('思维导图还未加载'); return }
  mindMapInstance.view.enlarge()
}

const zoomOut = () => {
  if (!mindMapInstance) { ElMessage.warning('思维导图还未加载'); return }
  mindMapInstance.view.narrow()
}

const fit = () => {
  if (!mindMapInstance) { ElMessage.warning('思维导图还未加载'); return }
  mindMapInstance.view.fit()
}

const resetView = () => {
  if (!mindMapInstance) { ElMessage.warning('思维导图还未加载'); return }
  mindMapInstance.view.reset()
}

const exportXmind = async () => {
  if (!mindMapInstance) { ElMessage.warning('思维导图还未加载'); return }
  try {
    if (!mindMapInstance.doExportXMind) {
      ElMessage.error('导出插件未注册')
      return
    }
    ElMessage.info('正在生成 XMind 文件...')
    const dataUrl = await mindMapInstance.export('xmind', '测试用例')
    const a = document.createElement('a')
    a.href = dataUrl
    a.download = '测试用例.xmind'
    a.click()
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
}, { deep: true })

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
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #ffffff;
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid #e5e7eb;
}

.mindmap-toolbar {
  padding: 10px 16px;
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  flex-shrink: 0;
}

.mindmap-container {
  flex: 1;
  width: 100%;
  min-height: 500px;
  background: #ffffff;
  overflow: hidden;
}
</style>

<style>
/* 编辑态文本框样式 (全局, 不能 scoped) */
.smm-node-edit-wrap {
  z-index: 1000 !important;
}
.smm-node-edit-wrap .ql-editor {
  min-width: 80px;
  padding: 4px 8px;
  border-radius: 4px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.12);
  border: 1px solid #4f46e5;
  background: #fff;
}
</style>
