<template>
  <div class="app-container">
    <!-- 主要内容区域 - 直接显示AboutView -->
    <router-view />
  </div>
</template>

<script>
import { onMounted } from 'vue';
import { useAppStore } from './store';

export default {
  name: 'App',
  components: {
  },
  setup() {
    const store = useAppStore();

    // 应用加载时执行的初始化操作
    onMounted(() => {
      // 检查系统主题偏好
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      if (prefersDark) {
        store.isDarkMode = true;
        store.updateThemeClass();
      }

      // 初始化API连接状态检查
      checkApiStatus();
    });

    // 检查API状态
    const checkApiStatus = async () => {
      try {
        store.setApiStatus('connecting');
        // 尝试连接到API
        const response = await fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001'}/health`, {
          method: 'GET',
          timeout: 5000
        });
        
        if (response.ok) {
          store.setApiStatus('connected');
        } else {
          store.setApiStatus('error');
        }
      } catch (error) {
        store.setApiStatus('error');
        console.log('API connection check failed:', error);
        // 这里不显示错误消息，因为我们在API服务中有模拟响应功能
      }
    };

    return {
      // 组件中不需要额外的返回值，所有状态都通过store管理
    };
  }
};
</script>

<style>
/* 应用容器样式 */
.app-container {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
  background-color: var(--background-color-base);
  color: var(--text-color-primary);
  transition: background-color 0.3s ease, color 0.3s ease;
  overflow: hidden;
}
</style>
