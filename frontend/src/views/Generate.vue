<template>
  <div class="h-full flex flex-col">
    <!-- Navbar removed since it's now in AdminLayout -->

    <main class="flex-grow w-full max-w-7xl mx-auto flex flex-col gap-8">
      
      <!-- Header Section -->
      <div>
        <h1 class="text-3xl font-bold text-gray-900 mb-2">智能用例生成</h1>
        <p class="text-gray-500">提供需求文档即可全自动生成结构化的测试用例。</p>
      </div>

      <!-- Generator Card -->
      <div class="bg-white rounded-2xl shadow-sm border border-gray-200 p-8 transition-all hover:shadow-md">
        <el-form :model="genForm" label-position="top">
          <!-- Source Selection -->
          <el-form-item label="需求来源文档">
            <el-radio-group v-model="genForm.sourceType" class="mt-2 w-full flex-wrap gap-4">
              <el-radio-button label="feishu" class="flex-grow flex-1 text-center">
                <div class="py-2 flex items-center justify-center gap-2">
                  <span class="i-mdi-file-document text-lg"></span> 飞书文档
                </div>
              </el-radio-button>
              <el-radio-button label="dingtalk" class="flex-grow flex-1 text-center">
                <div class="py-2 flex items-center justify-center gap-2">
                  <span class="i-mdi-message-text text-lg"></span> 钉钉文档
                </div>
              </el-radio-button>
              <el-radio-button label="local" class="flex-grow flex-1 text-center">
                <div class="py-2 flex items-center justify-center gap-2">
                  <span class="i-mdi-upload text-lg"></span> 本地文件上传
                </div>
              </el-radio-button>
            </el-radio-group>
          </el-form-item>

          <!-- Input Fields based on selection -->
          <div class="mt-6 mb-8 min-h-[100px] flex items-center justify-center bg-gray-50 rounded-xl border border-gray-100 p-6">
            
            <transition name="fade" mode="out-in">
              <!-- Link Input -->
              <div v-if="genForm.sourceType === 'feishu' || genForm.sourceType === 'dingtalk'" class="w-full max-w-2xl" :key="'link'">
                <label class="block text-sm font-medium text-gray-700 mb-2">在线文档链接</label>
                <el-input 
                  v-model="genForm.docUrl" 
                  :placeholder="genForm.sourceType === 'feishu' ? '请在此粘贴飞书文档链接...' : '请在此粘贴钉钉文档链接...'"
                  class="!rounded-xl"
                  size="large"
                >
                  <template #prefix>
                    <span class="text-gray-400">🔗</span>
                  </template>
                </el-input>
              </div>

              <!-- File Upload -->
              <div v-else-if="genForm.sourceType === 'local'" class="w-full max-w-2xl text-center" :key="'file'">
                <el-upload
                  class="upload-demo"
                  drag
                  action="#"
                  :auto-upload="false"
                  :on-change="handleFileChange"
                  :limit="1"
                >
                  <div class="el-upload__text text-gray-500 py-6">
                    <div class="text-4xl mb-4 opacity-50">📄</div>
                    将文件拖到此处，或 <em class="text-indigo-600 font-semibold not-italic">点击上传</em>
                  </div>
                  <template #tip>
                    <div class="el-upload__tip text-center mt-2 text-gray-400">
                      支持 Markdown, Word 或 PDF 格式文件。最大不超过 10MB。
                    </div>
                  </template>
                </el-upload>
              </div>
            </transition>
          </div>

          <!-- Action Button -->
          <div class="flex justify-end">
            <el-button 
              type="primary" 
              color="#4f46e5"
              size="large"
              class="!rounded-xl px-12 font-medium shadow-md shadow-indigo-200 hover:shadow-lg transition-all"
              @click="generate"
              :loading="isGenerating"
            >
              <template #icon>
                <span v-if="!isGenerating">✨</span>
              </template>
              {{ isGenerating ? '正在生成...' : '立即生成测试用例' }}
            </el-button>
          </div>
        </el-form>
      </div>

      <!-- Results Section -->
      <div v-if="generatedCases.length > 0" class="mt-8 animate-fade-in-up">
        <div class="flex items-center justify-between mb-6">
          <h2 class="text-2xl font-bold text-gray-900">生成的用例 <span class="text-sm font-normal text-gray-500 ml-2 bg-gray-200 px-2 py-1 rounded-full">共 {{ generatedCases.length }} 条结果</span></h2>
          <el-button type="success" plain class="!rounded-lg">
            导出为 Excel
          </el-button>
        </div>

        <el-table 
          :data="generatedCases" 
          border 
          style="width: 100%; border-radius: 12px; overflow: hidden; box-shadow: 0 1px 3px 0 rgb(0 0 0 / 0.1);"
          :header-cell-style="{ background: '#f8fafc', color: '#475569', fontWeight: '600', padding: '12px 16px' }"
          :cell-style="{ padding: '16px' }"
        >
          <el-table-column prop="id" label="编号" width="80" align="center" />
          <el-table-column prop="module" label="所属模块" width="150" />
          <el-table-column prop="title" label="用例标题" width="200" />
          <el-table-column prop="precondition" label="前置条件" />
          <el-table-column prop="steps" label="测试步骤">
            <template #default="scope">
              <pre class="font-sans whitespace-pre-wrap text-sm text-gray-600 m-0">{{ scope.row.steps }}</pre>
            </template>
          </el-table-column>
          <el-table-column prop="expected_result" label="预期结果" />
          <el-table-column prop="priority" label="优先级" width="100" align="center">
            <template #default="scope">
              <el-tag :type="scope.row.priority === 'High' ? 'danger' : 'warning'" effect="light" round size="small">
                {{ scope.row.priority }}
              </el-tag>
            </template>
          </el-table-column>
        </el-table>
      </div>

    </main>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import axios from 'axios'

const router = useRouter()
const isGenerating = ref(false)
const selectedFile = ref<any>(null)
const generatedCases = ref<any[]>([])

const genForm = reactive({
  sourceType: 'feishu',
  docUrl: ''
})

// Removed handleLogout as it's in AdminLayout

const handleFileChange = (file: any) => {
  selectedFile.value = file.raw
}

const generate = async () => {
  // Validate
  if (genForm.sourceType !== 'local' && !genForm.docUrl) {
    ElMessage.warning(`请输入${genForm.sourceType === 'feishu' ? '飞书' : '钉钉'}文档链接`)
    return
  }
  if (genForm.sourceType === 'local' && !selectedFile.value) {
    ElMessage.warning('请选择需要上传的文件')
    return
  }

  isGenerating.value = true
  generatedCases.value = [] // clear previous

  try {
    const formData = new FormData()
    formData.append('source_type', genForm.sourceType)
    if (genForm.sourceType !== 'local') {
      formData.append('doc_url', genForm.docUrl)
    } else {
      formData.append('file', selectedFile.value)
    }

    const response = await axios.post('http://127.0.0.1:8000/api/use_cases/generate', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
        'Authorization': `Bearer ${localStorage.getItem('token')}`
      }
    })

    if (response.data.status === 'success') {
      ElMessage.success('测试用例生成成功！')
      // Simulate typing/streaming effect or just show immediately
      setTimeout(() => {
        generatedCases.value = response.data.data
      }, 500)
    }
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '生成失败')
  } finally {
    isGenerating.value = false
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

.animate-fade-in-up {
  animation: fadeInUp 0.6s ease-out forwards;
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
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
/* override element plus default connecting borders */
:deep(.el-radio-button:first-child .el-radio-button__inner) {
  border-radius: 0.75rem !important;
}
:deep(.el-radio-button:last-child .el-radio-button__inner) {
  border-radius: 0.75rem !important;
}
:deep(.el-input__wrapper) {
  box-shadow: 0 1px 2px 0 rgb(0 0 0 / 0.05);
  padding: 8px 15px;
}
:deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px #4f46e5 inset;
}
</style>
