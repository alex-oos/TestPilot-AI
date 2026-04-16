<template>
  <div class="space-y-6">
    <AIModelConfig v-if="activeSection === 'ai'" />
    <PromptConfig v-else-if="activeSection === 'prompts'" />
    <BehaviorConfig v-else-if="activeSection === 'behavior'" />
    <NotificationConfig v-else-if="activeSection === 'notifications'" />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import AIModelConfig from './config/AIModelConfig.vue'
import PromptConfig from './config/PromptConfig.vue'
import BehaviorConfig from './config/BehaviorConfig.vue'
import NotificationConfig from './config/NotificationConfig.vue'

const route = useRoute()

const activeSection = computed<'ai' | 'prompts' | 'notifications' | 'behavior'>(() => {
  if (route.path.endsWith('/prompts')) return 'prompts'
  if (route.path.endsWith('/notifications')) return 'notifications'
  if (route.path.endsWith('/behavior')) return 'behavior'
  return 'ai'
})
</script>
