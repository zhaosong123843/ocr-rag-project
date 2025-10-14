<template>
  <header class="app-header">
    <div class="header-content">
      <!-- 移动端菜单按钮 -->
      <button
        class="mobile-menu-btn"
        @click="toggleMobileMenu"
        v-if="isMobile"
      >
        <el-icon><menu /></el-icon>
      </button>

      <!-- 品牌Logo -->
      <div class="logo-container">
        <el-icon class="logo-icon"><document /></el-icon>
        <h1 class="logo-text gradient-text">
          多模态<span class="highlight">RAG</span>检索系统
        </h1>
      </div>

      <!-- 导航链接 -->
      <nav class="main-nav" v-if="!isMobile">
        <router-link to="/" class="nav-link">多模态RAG检索系统</router-link>
      </nav>

      <!-- 右侧功能区 -->
      <div class="header-actions">
        <!-- 深色模式切换 -->
        <button
          class="theme-toggle"
          @click="toggleTheme"
          :title="isDarkMode ? '切换到浅色模式' : '切换到深色模式'"
        >
          <el-icon v-if="isDarkMode"><sunny /></el-icon>
          <el-icon v-else><moon /></el-icon>
        </button>

        <!-- 帮助按钮 -->
        <el-popover
          placement="bottom"
          title="使用指南"
          width="300"
          trigger="click"
        >
          <template #reference>
            <button class="help-btn">
              <el-icon><help-filled /></el-icon>
            </button>
          </template>
          <div class="help-content">
            <h4>如何使用?</h4>
            <ol>
              <li>上传PDF文档</li>
              <li>等待文档解析和索引</li>
              <li>在聊天框中提问</li>
              <li>查看AI回答和引用源</li>
            </ol>
            <div class="help-link">
              <a href="#" class="learn-more">查看完整教程</a>
            </div>
          </div>
        </el-popover>
      </div>
    </div>

    <!-- 移动端菜单 -->
    <div
      class="mobile-menu-overlay"
      v-if="mobileMenuOpen"
      @click="closeMobileMenu"
    ></div>
    <div class="mobile-menu" :class="{ open: mobileMenuOpen }">
      <nav class="mobile-nav">
        <router-link to="/" class="mobile-nav-link" @click="closeMobileMenu">
          首页
        </router-link>
        <router-link to="/about" class="mobile-nav-link" @click="closeMobileMenu">
          关于
        </router-link>
        <button
          class="mobile-nav-link"
          @click="closeMobileMenu"
        >
          设置
        </button>
      </nav>
    </div>
  </header>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { useAppStore } from '@/store';
import { Document, Menu, Moon, HelpFilled, Sunny } from '@element-plus/icons-vue';

const store = useAppStore();
const mobileMenuOpen = ref(false);
const isMobile = ref(false);

// 计算属性
const isDarkMode = computed(() => store.isDarkTheme);

// 检测窗口大小变化
const handleResize = () => {
  isMobile.value = window.innerWidth < 768;
};

// 生命周期钩子
onMounted(() => {
  handleResize();
  window.addEventListener('resize', handleResize);
  // 初始化主题类
  store.updateThemeClass();
});

onUnmounted(() => {
  window.removeEventListener('resize', handleResize);
});

// 方法
const toggleMobileMenu = () => {
  mobileMenuOpen.value = !mobileMenuOpen.value;
  store.toggleMobileMenu();
};

const closeMobileMenu = () => {
  mobileMenuOpen.value = false;
  store.toggleMobileMenu();
};

const toggleTheme = () => {
  store.toggleDarkMode();
};
</script>

<style scoped>
.app-header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 1000;
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid var(--border-color);
  transition: all 0.3s ease;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
}

.header-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 1.5rem;
  max-width: 1400px;
  margin: 0 auto;
}

/* 移动端菜单按钮 */
.mobile-menu-btn {
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: var(--text-color);
  padding: 0.5rem;
  border-radius: var(--border-radius);
  transition: background-color 0.2s;
}

.mobile-menu-btn:hover {
  background-color: var(--hover-color);
}

/* Logo样式 */
.logo-container {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.logo-icon {
  font-size: 1.5rem;
  color: var(--primary-color);
}

.logo-text {
  font-size: 1.25rem;
  font-weight: 700;
  margin: 0;
}

.gradient-text {
  background: linear-gradient(90deg, var(--primary-color), var(--secondary-color));
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  display: inline-block;
}

.highlight {
  color: var(--secondary-color);
  background: none;
  -webkit-background-clip: none;
  background-clip: none;
}

/* 导航样式 */
.main-nav {
  display: flex;
  gap: 1.5rem;
}

.nav-link {
  text-decoration: none;
  color: var(--text-color);
  font-weight: 500;
  padding: 0.5rem 0;
  position: relative;
  transition: color 0.2s;
}

.nav-link:hover {
  color: var(--primary-color);
}

.nav-link::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  width: 0;
  height: 2px;
  background-color: var(--primary-color);
  transition: width 0.2s;
}

.nav-link:hover::after {
  width: 100%;
}

/* 右侧功能区 */
.header-actions {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.theme-toggle,
.help-btn {
  background: none;
  border: none;
  font-size: 1.25rem;
  cursor: pointer;
  color: var(--text-color);
  padding: 0.5rem;
  border-radius: var(--border-radius);
  transition: all 0.2s;
}

.theme-toggle:hover,
.help-btn:hover {
  background-color: var(--hover-color);
  color: var(--primary-color);
}

/* 帮助内容样式 */
.help-content h4 {
  margin-top: 0;
  color: var(--primary-color);
}

.help-content ol {
  padding-left: 1.5rem;
  margin: 1rem 0;
}

.help-content li {
  margin-bottom: 0.5rem;
  line-height: 1.5;
}

.help-link {
  margin-top: 1rem;
  text-align: right;
}

.learn-more {
  color: var(--primary-color);
  text-decoration: none;
  font-weight: 500;
  transition: color 0.2s;
}

.learn-more:hover {
  color: var(--secondary-color);
}

/* 移动端菜单样式 */
.mobile-menu-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  z-index: 998;
}

.mobile-menu {
  position: fixed;
  top: 0;
  right: -300px;
  width: 300px;
  height: 100vh;
  background-color: var(--bg-color);
  box-shadow: -2px 0 10px rgba(0, 0, 0, 0.1);
  z-index: 999;
  transition: right 0.3s ease;
}

.mobile-menu.open {
  right: 0;
}

.mobile-nav {
  display: flex;
  flex-direction: column;
  padding: 2rem 1rem;
  gap: 1rem;
}

.mobile-nav-link {
  text-decoration: none;
  color: var(--text-color);
  font-size: 1.1rem;
  padding: 1rem;
  border-radius: var(--border-radius);
  transition: all 0.2s;
  background: none;
  border: none;
  text-align: left;
  cursor: pointer;
}

.mobile-nav-link:hover {
  background-color: var(--hover-color);
  color: var(--primary-color);
}

/* 响应式设计 */
@media (max-width: 768px) {
  .header-content {
    padding: 0.75rem 1rem;
  }

  .logo-text {
    font-size: 1.1rem;
  }

  .main-nav {
    display: none;
  }
}

/* 深色模式适配 */
.dark .app-header {
  background: rgba(15, 23, 42, 0.8);
  border-bottom-color: var(--border-color-dark);
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
}
</style>