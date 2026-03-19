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
            <!-- URL Input -->
            <div v-if="genForm.sourceType !== 'local'" class="w-full max-w-2xl" :key="'link'">
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
            <div v-else class="w-full max-w-2xl text-center" :key="'file'">
              <el-upload
                drag
                action="#"
                :auto-upload="false"
                :on-change="handleFileChange"
                :limit="1"
                :on-exceed="() => ElMessage.warning('每次只能上传一个文件')"
              >
                <div class="el-upload__text text-gray-500 py-6">
                  <div class="text-4xl mb-4 opacity-50">📄</div>
                  将文件拖到此处，或 <em class="text-indigo-600 font-semibold not-italic">点击上传</em>
                  <div v-if="selectedFile" class="mt-3 text-indigo-600 font-medium text-sm">
                    ✅ 已选择：{{ selectedFile.name }}
                  </div>
                </div>
                <template #tip>
                  <div class="el-upload__tip text-center mt-2 text-gray-400">
                    支持 Markdown、Word (.docx) 或 PDF 格式，最大 10MB
                  </div>
                </template>
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
import axios from 'axios'
import { addTaskToHistory } from '../utils/taskHistory'

const router = useRouter()
const isSubmitting = ref(false)
const selectedFile = ref<any>(null)

const genForm = reactive({
  sourceType: 'local',
  docUrl: ''
})

const handleFileChange = (file: any) => {
  selectedFile.value = file.raw
}

const submit = async () => {
  // Validate
  if (genForm.sourceType !== 'local' && !genForm.docUrl) {
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
    if (genForm.sourceType !== 'local') {
      formData.append('doc_url', genForm.docUrl)
    } else {
      formData.append('file', selectedFile.value)
    }

    const response = await axios.post(
      '/api/use_cases/submit',
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      }
    )

    if (response.data.status === 'success') {
      const taskId = response.data.task_id
      const sourceLabel = genForm.sourceType === 'feishu'
        ? '飞书文档'
        : genForm.sourceType === 'dingtalk'
          ? '钉钉文档'
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
    ElMessage.error(error.response?.data?.detail || '提交失败，请重试')
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
</style>
