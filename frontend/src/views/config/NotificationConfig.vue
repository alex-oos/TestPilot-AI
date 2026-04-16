<template>
  <section class="config-page config-page-full" v-loading="loading">
    <div class="notification-header">
      <h1 class="text-4xl font-bold text-white">⚙️ 消息通知配置</h1>
      <p class="text-white/80 mt-2">配置飞书、企微、钉钉Webhook机器人地址</p>
    </div>

    <div class="bg-white rounded-2xl border border-slate-200 overflow-hidden">
      <el-tabs v-model="activeNotifyTab" class="px-4">
        <el-tab-pane label="飞书机器人" name="feishu" />
        <el-tab-pane label="企微机器人" name="wecom" />
        <el-tab-pane label="钉钉机器人" name="dingtalk" />
      </el-tabs>

      <div class="p-5 border-t border-slate-200 space-y-4">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4 items-end">
          <el-form-item label="机器人名称">
            <el-input v-model="currentNotifyConfig.name" :placeholder="`请输入${notifyTabLabel(activeNotifyTab)}名称`" />
          </el-form-item>
          <el-form-item label="启用">
            <el-switch v-model="currentNotifyConfig.enabled" />
          </el-form-item>
        </div>

        <el-form-item label="Webhook URL">
          <el-input v-model="currentNotifyConfig.webhook" placeholder="请输入Webhook URL" />
        </el-form-item>

        <el-form-item label="签名 Secret（可选）">
          <el-input v-model="currentNotifyConfig.secret" placeholder="请输入 Secret" />
        </el-form-item>

        <el-form-item label="自定义关键词（可选）">
          <el-input v-model="currentNotifyConfig.custom_keyword" placeholder="请输入自定义关键词（如：@all）" />
        </el-form-item>

        <div class="pt-4 border-t border-slate-200 flex justify-end">
          <el-button type="primary" :loading="saving" @click="saveNotificationChannel(activeNotifyTab)">
            保存{{ notifyTabLabel(activeNotifyTab) }}配置
          </el-button>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  editNotification,
  getNotifications,
} from '../../api/config-center'

const loading = ref(false)
const saving = ref(false)
const activeNotifyTab = ref<'feishu' | 'wecom' | 'dingtalk'>('feishu')

const notifications = reactive({
  feishu: { name: '', enabled: false, webhook: '', secret: '', custom_keyword: '' },
  dingtalk: { name: '', enabled: false, webhook: '', secret: '', custom_keyword: '' },
  wecom: { name: '', enabled: false, webhook: '', secret: '', custom_keyword: '' },
})

const currentNotifyConfig = computed(() => {
  return notifications[activeNotifyTab.value]
})

function notifyTabLabel(tab: 'feishu' | 'wecom' | 'dingtalk') {
  if (tab === 'feishu') return '飞书机器人'
  if (tab === 'wecom') return '企微机器人'
  return '钉钉机器人'
}

function applyNotificationConfig(data: any) {
  Object.assign(notifications.feishu, data?.notifications?.feishu || {})
  Object.assign(notifications.dingtalk, data?.notifications?.dingtalk || {})
  Object.assign(notifications.wecom, data?.notifications?.wecom || {})
}

async function fetchConfig() {
  loading.value = true
  try {
    const resp = await getNotifications()
    applyNotificationConfig(resp.data?.data || {})
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.msg || e?.response?.data?.detail || '加载配置失败')
  } finally {
    loading.value = false
  }
}

async function saveNotificationChannel(tab: 'feishu' | 'wecom' | 'dingtalk') {
  saving.value = true
  try {
    const current = notifications[tab]
    const payload = {
      name: current.name,
      enabled: current.enabled,
      webhook: current.webhook,
      secret: current.secret,
      custom_keyword: current.custom_keyword,
    }
    const resp = await editNotification(tab, payload)
    applyNotificationConfig(resp.data?.data || {})
    ElMessage.success(`${notifyTabLabel(tab)}配置已保存`)
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.msg || e?.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  fetchConfig()
})
</script>

<style scoped>
.config-page {
  max-width: 1280px;
  margin: 0 auto;
}

.config-page-full {
  max-width: none;
}

.notification-header {
  background: linear-gradient(120deg, #4f7ee8 0%, #6f4bb8 100%);
  border-radius: 14px;
  padding: 26px 24px;
}
</style>
