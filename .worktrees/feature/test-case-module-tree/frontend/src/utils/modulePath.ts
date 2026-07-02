/**
 * 模块路径解析与多级树构建工具。
 *
 * @author Zhao Wang
 */

export interface ModuleTreeNode {
  /** 当前层级名称 */
  name: string
  /** 从根到当前节点的完整路径 */
  fullPath: string
  /** 该节点及子树下用例总数 */
  count: number
  /** 子模块 */
  children: ModuleTreeNode[]
}

export interface ModuleTrieNode {
  name: string
  fullPath: string
  count: number
  cases: unknown[]
  children: Map<string, ModuleTrieNode>
}

/** 解析 module 字段为多级路径段 */
export function parseModulePath(module: string | null | undefined): string[] {
  const cleaned = String(module || '').replace(/<[^>]+>/g, '').trim()
  if (!cleaned) return []
  if (cleaned.includes(' / ')) {
    return cleaned.split(' / ').map(s => s.trim()).filter(Boolean)
  }
  if (cleaned.includes('/')) {
    return cleaned.split('/').map(s => s.trim()).filter(Boolean)
  }
  return [cleaned]
}

/** 将路径段合并为存储用 module 字符串 */
export function joinModulePath(segments: string[]): string {
  return segments.filter(Boolean).join(' / ')
}

/** 判断用例 module 是否位于指定路径前缀下（含精确匹配） */
export function moduleMatchesPrefix(module: string | null | undefined, prefixPath: string): boolean {
  if (!prefixPath) return true
  const mod = String(module || '').trim()
  if (!mod) return false
  if (mod === prefixPath) return true
  return mod.startsWith(`${prefixPath} / `) || mod.startsWith(`${prefixPath}/`)
}

/** 从 flat module 计数构建多级模块树 */
export function buildModuleTree(entries: Array<{ name: string; count: number }>): ModuleTreeNode[] {
  const root = new Map<string, ModuleTrieNode>()

  const ensureNode = (
    level: Map<string, ModuleTrieNode>,
    segments: string[],
    index: number,
  ): ModuleTrieNode => {
    const name = segments[index]
    const fullPath = joinModulePath(segments.slice(0, index + 1))
    if (!level.has(name)) {
      level.set(name, { name, fullPath, count: 0, cases: [], children: new Map() })
    }
    return level.get(name)!
  }

  for (const entry of entries) {
    const segments = parseModulePath(entry.name)
    if (!segments.length) continue
    let level = root
    for (let i = 0; i < segments.length; i++) {
      const node = ensureNode(level, segments, i)
      node.count += entry.count
      level = node.children
    }
  }

  const toTree = (map: Map<string, ModuleTrieNode>): ModuleTreeNode[] =>
    [...map.values()]
      .sort((a, b) => a.name.localeCompare(b.name, 'zh-CN'))
      .map(node => ({
        name: node.name,
        fullPath: node.fullPath,
        count: node.count,
        children: toTree(node.children),
      }))

  return toTree(root)
}

/** 需求根节点 selection key */
export function reqRootKey(reqId: number): string {
  return `req:${reqId}`
}

/** 需求下模块路径 selection key */
export function reqModulePathKey(reqId: number, fullPath: string): string {
  return `req:${reqId}#${fullPath}`
}

/** 独立模块路径 selection key */
export function standaloneModulePathKey(fullPath: string): string {
  return `mod#${fullPath}`
}

/** 模块树节点 expand key */
export function moduleExpandKey(scope: string, fullPath: string): string {
  return `${scope}::${fullPath}`
}

export function parseModuleSelection(sel: string): {
  kind: 'all' | 'unassigned' | 'requirement' | 'requirement_path' | 'standalone_path' | 'legacy'
  requirementId?: number
  modulePath?: string
  legacyModule?: string
} {
  if (sel === '__unassigned__') return { kind: 'unassigned' }
  if (sel.startsWith('req:') && sel.includes('#')) {
    const hashIdx = sel.indexOf('#')
    return {
      kind: 'requirement_path',
      requirementId: Number(sel.slice(4, hashIdx)),
      modulePath: sel.slice(hashIdx + 1),
    }
  }
  if (sel.startsWith('req:')) {
    return { kind: 'requirement', requirementId: Number(sel.slice(4)) }
  }
  if (sel.startsWith('mod#')) {
    return { kind: 'standalone_path', modulePath: sel.slice(4) }
  }
  return { kind: 'legacy', legacyModule: sel }
}

interface CaseMindMapTrieNode {
  name: string
  fullPath: string
  cases: unknown[]
  children: Map<string, CaseMindMapTrieNode>
}

/** 将用例按 module 路径构建多级模块脑图分支 */
export function buildCaseModuleMindMapBranches<T>(
  cases: T[],
  getModule: (item: T) => string | null | undefined,
  toCaseNode: (item: T) => unknown,
  requirementId?: number,
): Array<{ content: string; children: unknown[]; payload?: Record<string, unknown> }> {
  const root = new Map<string, CaseMindMapTrieNode>()

  const ensure = (
    level: Map<string, CaseMindMapTrieNode>,
    segments: string[],
    index: number,
  ): CaseMindMapTrieNode => {
    const name = segments[index]
    const fullPath = joinModulePath(segments.slice(0, index + 1))
    if (!level.has(name)) {
      level.set(name, { name, fullPath, cases: [], children: new Map() })
    }
    return level.get(name)!
  }

  for (const item of cases) {
    const segments = parseModulePath(getModule(item))
    if (!segments.length) continue
    let level = root
    for (let i = 0; i < segments.length; i++) {
      const node = ensure(level, segments, i)
      if (i === segments.length - 1) node.cases.push(item)
      level = node.children
    }
  }

  const toNodes = (map: Map<string, CaseMindMapTrieNode>): Array<{
    content: string
    children: unknown[]
    payload?: Record<string, unknown>
  }> =>
    [...map.values()]
      .sort((a, b) => a.name.localeCompare(b.name, 'zh-CN'))
      .map(node => ({
        content: node.name,
        children: [
          ...toNodes(node.children),
          ...node.cases.map(item => toCaseNode(item)),
        ],
        payload: {
          type: 'module',
          module_path: node.fullPath,
          ...(requirementId != null ? { requirement_id: requirementId } : {}),
        },
      }))

  return toNodes(root)
}
