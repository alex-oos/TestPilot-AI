<template>
  <div v-for="node in nodes" :key="nodeKey(node)" class="mb-0.5">
    <div
      class="flex items-center justify-between rounded-lg cursor-pointer transition-colors"
      :class="[
        isSelected(node) ? 'bg-indigo-50 text-indigo-700' : 'hover:bg-gray-50 text-gray-600',
        depth === 0 ? 'px-3 py-1.5' : 'px-2 py-1',
      ]"
      :style="{ paddingLeft: `${12 + depth * 12}px` }"
      @click="emit('select', node)"
    >
      <div class="flex items-center gap-1 flex-1 min-w-0" @click.stop="toggle(node)">
        <span v-if="node.children.length" class="text-xs text-gray-400 w-3 shrink-0">
          {{ isExpanded(node) ? '▼' : '▶' }}
        </span>
        <span v-else class="w-3 shrink-0" />
        <span class="text-sm truncate" :title="node.name">{{ node.name }}</span>
      </div>
      <span class="text-xs bg-gray-100 text-gray-500 px-2 py-0.5 rounded-full ml-1 shrink-0">{{ node.count }}</span>
    </div>
    <ModuleTreeNodes
      v-if="node.children.length && isExpanded(node)"
      :nodes="node.children"
      :depth="depth + 1"
      :scope="scope"
      :requirement-id="requirementId"
      :selected-key="selectedKey"
      :expanded-keys="expandedKeys"
      @select="emit('select', $event)"
      @toggle="emit('toggle', $event)"
    />
  </div>
</template>

<script setup lang="ts">
import type { ModuleTreeNode } from '../utils/modulePath'
import { moduleExpandKey, reqModulePathKey, standaloneModulePathKey } from '../utils/modulePath'

defineOptions({ name: 'ModuleTreeNodes' })

const props = defineProps<{
  nodes: ModuleTreeNode[]
  depth?: number
  scope: 'requirement' | 'standalone'
  requirementId?: number
  selectedKey: string | null
  expandedKeys: Set<string>
}>()

const emit = defineEmits<{
  (e: 'select', node: ModuleTreeNode): void
  (e: 'toggle', node: ModuleTreeNode): void
}>()

const depth = props.depth ?? 0

function nodeKey(node: ModuleTreeNode) {
  return `${props.scope}-${props.requirementId ?? 's'}-${node.fullPath}`
}

function selectionKey(node: ModuleTreeNode): string {
  if (props.scope === 'requirement' && props.requirementId != null) {
    return reqModulePathKey(props.requirementId, node.fullPath)
  }
  return standaloneModulePathKey(node.fullPath)
}

function expandKey(node: ModuleTreeNode): string {
  const scope = props.scope === 'requirement'
    ? `req-${props.requirementId}`
    : 'standalone'
  return moduleExpandKey(scope, node.fullPath)
}

function isSelected(node: ModuleTreeNode) {
  return props.selectedKey === selectionKey(node)
}

function isExpanded(node: ModuleTreeNode) {
  return props.expandedKeys.has(expandKey(node))
}

function toggle(node: ModuleTreeNode) {
  if (!node.children.length) return
  emit('toggle', node)
}
</script>
