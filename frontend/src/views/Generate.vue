<template>
  <div class="space-y-8">
    <!-- Header -->
    <div>
      <h1 class="text-3xl font-bold text-gray-900 mb-2">智能用例生成</h1>
      <p class="text-gray-500">上传需求文档，AI 自动完成需求分析 → 用例编写 → 用例评审全流程。</p>
    </div>

    <!-- Generator Card -->
    <div class="bg-white rounded-2xl shadow-sm border border-gray-200 p-8">
      <el-form :model="genForm" label-position="top">
        <!-- Source Selection -->
        <el-form-item label="需求来源文档">
          <el-radio-group v-model="genForm.sourceType" class="mt-2 w-full flex-wrap gap-4">
            <el-radio-button label="feishu" class="flex-grow flex-1 text-center">
              <div class="py-2 flex items-center justify-center gap-2">
                <span>📄</span> 飞书文档
              </div>
            </el-radio-button>
            <el-radio-button label="dingtalk" class="flex-grow flex-1 text-center">
              <div class="py-2 flex items-center justify-center gap-2">
                <span>💬</span> 钉钉文档
              </div>
            </el-radio-button>
            <el-radio-button label="manual" class="flex-grow flex-1 text-center">
              <div class="py-2 flex items-center justify-center gap-2">
                <span>✍️</span> 手动输入需求描述
              </div>
            </el-radio-button>
            <el-radio-button label="local" class="flex-grow flex-1 text-center">
              <div class="py-2 flex items-center justify-center gap-2">
                <span>📁</span> 本地文件上传
              </div>
            </el-radio-button>
          </el-radio-group>
        </el-form-item>

        <!-- Input Area -->
        <div class="mt-6 mb-8 min-h-[120px] flex items-center justify-center bg-gray-50 rounded-xl border border-gray-100 p-6">
          <transition name="fade" mode="out-in">
            <!-- Manual Input -->
            <div v-if="genForm.sourceType === 'manual'" class="w-full max-w-6xl" :key="'manual'">
              <div class="manual-title">✍️ 手动输入需求描述</div>
              <div class="manual-form-grid">
                <div>
                  <label class="manual-label">需求标题 <span class="required">*</span></label>
                  <el-input
                    v-model="genForm.manualTitle"
                    placeholder="请输入需求标题，如：用户登录功能需求"
                    size="large"
                  />
                </div>
                <div>
                  <label class="manual-label">需求描述 <span class="required">*</span></label>
                  <el-input
                    v-model="genForm.manualDescription"
                    type="textarea"
                    :rows="8"
                    maxlength="2000"
                    show-word-limit
                    resize="none"
                    placeholder="请详细描述您的需求，包括功能描述、使用场景、业务流程等"
                  />
                </div>
                <div>
                  <label class="manual-label">关联项目（可选）</label>
                  <el-input
                    v-model="genForm.relatedProject"
                    placeholder="请输入关联项目名称，如：AI 测试平台"
                    size="large"
                  />
                </div>
              </div>
            </div>

            <!-- URL Input -->
            <div v-else-if="genForm.sourceType !== 'local'" class="w-full max-w-2xl" :key="'link'">
              <label class="block text-sm font-medium text-gray-700 mb-2">在线文档链接</label>
              <el-input
                v-model="genForm.docUrl"
                :placeholder="genForm.sourceType === 'feishu' ? '请粘贴飞书文档链接...' : '请粘贴钉钉文档链接...'"
                size="large"
              >
                <template #prefix><span class="text-gray-400">🔗</span></template>
              </el-input>
            </div>

            <!-- File Upload -->
            <div v-else class="w-full max-w-5xl text-left" :key="'file'">
              <el-upload
                class="demand-upload"
                drag
                action="#"
                :auto-upload="false"
                :on-change="handleFileChange"
                :show-file-list="false"
                :limit="1"
                :on-exceed="() => ElMessage.warning('每次只能上传一个文件')"
                accept=".pdf,.docx,.txt,.md,.markdown,.json,.yaml,.yml"
              >
                <div class="upload-content">
                  <div class="upload-folder-icon">📁</div>
                  <p class="upload-main-text">拖拽文件到此处或点击选择文件</p>
                  <p class="upload-sub-text">支持 PDF、Word、TXT、Markdown、JSON、YAML、PNG、JPG、JPEG、WEBP、BMP、GIF（图片自动识别）</p>
                  <el-button type="primary" color="#3b95d9" class="upload-select-btn">选择文件</el-button>
                  <div v-if="selectedFile" class="upload-selected-text">
                    已选择：{{ selectedFile.name }}
                  </div>
                </div>
              </el-upload>
            </div>
          </transition>
        </div>

        <!-- Submit Button -->
        <div class="flex justify-end">
          <el-button
            type="primary"
            color="#4f46e5"
            size="large"
            class="!rounded-xl px-12 font-medium shadow-md shadow-indigo-200 hover:shadow-lg transition-all"
            @click="submit"
            :loading="isSubmitting"
          >
            <template #icon>
              <span v-if="!isSubmitting">✨</span>
            </template>
            {{ isSubmitting ? '正在提交...' : '立即生成用例' }}
          </el-button>
        </div>
      </el-form>
    </div>

    <!-- Recent Tasks Hint -->
    <div class="text-center text-sm text-gray-400">
      提交后将自动跳转至任务详情页，实时查看 AI 分析进度 🚀
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { addTaskToHistory } from '../utils/taskHistory'
import { createTask } from '../api/generate'

const router = useRouter()
const isSubmitting = ref(false)
const selectedFile = ref<File | null>(null)

const genForm = reactive({
  sourceType: 'feishu',
  docUrl: '',
  manualTitle: '',
  manualDescription: '',
  relatedProject: ''
})

const handleFileChange = (file: any) => {
  selectedFile.value = file.raw
}

const submit = async () => {
  // Validate
  if (genForm.sourceType === 'manual') {
    if (!genForm.manualTitle.trim()) {
      ElMessage.warning('请输入需求标题')
      return
    }
    if (!genForm.manualDescription.trim()) {
      ElMessage.warning('请输入需求描述')
      return
    }
  } else if (genForm.sourceType !== 'local' && !genForm.docUrl) {
    ElMessage.warning(`请输入${genForm.sourceType === 'feishu' ? '飞书' : '钉钉'}文档链接`)
    return
  }
  if (genForm.sourceType === 'local' && !selectedFile.value) {
    ElMessage.warning('请选择需要上传的文件')
    return
  }

  isSubmitting.value = true

  try {
    const formData = new FormData()
    formData.append('source_type', genForm.sourceType)
    formData.append('submitter', localStorage.getItem('username') || 'admin')
    if (genForm.sourceType === 'manual') {
      formData.append('manual_title', genForm.manualTitle.trim())
      formData.append('manual_description', genForm.manualDescription.trim())
      if (genForm.relatedProject.trim()) {
        formData.append('related_project', genForm.relatedProject.trim())
      }
    } else if (genForm.sourceType !== 'local') {
      formData.append('doc_url', genForm.docUrl)
    } else {
      if (!selectedFile.value) {
        ElMessage.warning('请选择需要上传的文件')
        isSubmitting.value = false
        return
      }
      formData.append('file', selectedFile.value)
    }

    const response = await createTask(formData)

    if (response.data.code === 0) {
      const taskId = response.data?.data?.task_id
      const sourceLabel = genForm.sourceType === 'feishu'
        ? '飞书文档'
        : genForm.sourceType === 'dingtalk'
          ? '钉钉文档'
          : genForm.sourceType === 'manual'
            ? '手动输入'
            : '本地文件'

      addTaskToHistory({
        id: taskId,
        sourceType: genForm.sourceType,
        sourceLabel
      })

      ElMessage.success('任务已提交，正在跳转...')
      router.push(`/task/${taskId}`)
    }
  } catch (error: any) {
    ElMessage.error(error.response?.data?.msg || error.response?.data?.detail || '提交失败，请重试')
  } finally {
    isSubmitting.value = false
  }
}
</script>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease, transform 0.3s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
  transform: translateY(10px);
}

:deep(.el-radio-button__inner) {
  width: 100%;
  border-radius: 0.75rem !important;
  border: 1px solid #e2e8f0 !important;
  background-color: white;
  color: #475569;
  box-shadow: none !important;
  transition: all 0.2s;
}
:deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) {
  background-color: #e0e7ff;
  border-color: #818cf8 !important;
  color: #4338ca;
  box-shadow: 0 0 0 1px #818cf8 !important;
}
:deep(.el-radio-button) {
  margin: 0 !important;
  border-radius: 0.75rem;
}
:deep(.el-radio-button:first-child .el-radio-button__inner) { border-radius: 0.75rem !important; }
:deep(.el-radio-button:last-child .el-radio-button__inner) { border-radius: 0.75rem !important; }
:deep(.el-input__wrapper) {
  box-shadow: 0 1px 2px 0 rgb(0 0 0 / 0.05);
  padding: 8px 15px;
}
:deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px #4f46e5 inset;
}

.demand-upload {
  width: 100%;
}

:deep(.demand-upload .el-upload),
:deep(.demand-upload .el-upload-dragger) {
  width: 100%;
}

:deep(.demand-upload .el-upload-dragger) {
  border: 2px dashed #d5d7dd;
  border-radius: 12px;
  background: #fff;
  padding: 48px 24px 40px;
}

:deep(.demand-upload .el-upload-dragger:hover) {
  border-color: #90b6e8;
}

.upload-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 210px;
  text-align: center;
}

.upload-folder-icon {
  font-size: 58px;
  line-height: 1;
  margin-bottom: 20px;
}

.upload-main-text {
  font-size: 30px;
  color: #4b5563;
  margin: 0 0 8px;
}

.upload-sub-text {
  margin: 0 0 22px;
  color: #9ca3af;
  font-size: 14px;
}

.upload-select-btn {
  height: 38px;
  border-radius: 8px;
  padding: 0 24px;
}

.upload-selected-text {
  margin-top: 12px;
  color: #2563eb;
  font-size: 14px;
  font-weight: 500;
}

.manual-title {
  font-size: 22px;
  font-weight: 700;
  color: #1f2937;
  margin-bottom: 18px;
}

.manual-form-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 16px;
}

.manual-label {
  display: block;
  margin-bottom: 8px;
  color: #374151;
  font-size: 14px;
  font-weight: 600;
}

.required {
  color: #ef4444;
}

:deep(.el-textarea__inner) {
  border-radius: 10px;
}
</style>
