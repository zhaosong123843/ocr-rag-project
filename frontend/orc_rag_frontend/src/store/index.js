// Pinia Store - 全局状态管理
import { defineStore } from 'pinia';

export const useAppStore = defineStore('app', {
  state: () => ({
    // 聊天相关状态
    chatMessages: [],
    currentSessionId: 'default',
    isLoading: false,
    
    // PDF相关状态
    activePdfFile: null,
    pdfPage: 1,
    pdfZoom: 1.0,
    
    // 应用UI状态
    isDarkMode: false,
    sidebarCollapsed: false,
    mobileMenuOpen: false,
    
    // 系统状态
    apiStatus: 'idle',
  }),
  
  getters: {
    // 获取当前聊天消息列表
    getChatMessages: (state) => state.chatMessages,
    
    // 获取活跃的PDF文件
    getActivePdfFile: (state) => state.activePdfFile,
    
    // 检查是否有活跃的PDF文件
    hasActivePdf: (state) => state.activePdfFile !== null,
    
    // 获取当前PDF页面
    getPdfPage: (state) => state.pdfPage,
    
    // 获取当前PDF缩放比例
    getPdfZoom: (state) => state.pdfZoom,
    
    // 检查是否为深色模式
    isDarkTheme: (state) => state.isDarkMode,
    
    // 检查是否正在加载
    getIsLoading: (state) => state.isLoading,
  },
  
  actions: {
    // 添加聊天消息
    addChatMessage(message) {
      const newMessage = {
        ...message,
        id: Date.now().toString() + Math.random().toString(36).substr(2, 9),
        createdAt: new Date(),
      };
      this.chatMessages.push(newMessage);
      return newMessage;
    },
    
    // 更新消息内容（用于流式响应）
    updateChatMessage(id, updates) {
      const messageIndex = this.chatMessages.findIndex(msg => msg.id === id);
      if (messageIndex !== -1) {
        this.chatMessages[messageIndex] = {
          ...this.chatMessages[messageIndex],
          ...updates,
        };
      }
    },
    
    // 清空聊天记录
    clearChatMessages() {
      this.chatMessages = [];
    },
    
    // 设置活跃的PDF文件
    setActivePdfFile(file) {
      this.activePdfFile = file;
      if (file) {
        this.pdfPage = 1; // 重置到第一页
      }
    },
    
    // 更新PDF解析进度
    updatePdfParseProgress(progress) {
      if (this.activePdfFile) {
        this.activePdfFile.parseProgress = progress;
        this.activePdfFile.isParsing = progress < 100;
        this.activePdfFile.isParsed = progress === 100;
      }
    },
    
    // 设置PDF索引状态
    setPdfIndexed(indexed) {
      if (this.activePdfFile) {
        this.activePdfFile.isIndexed = indexed;
      }
    },
    
    // 设置PDF解析错误
    setPdfParseError(error) {
      if (this.activePdfFile) {
        this.activePdfFile.error = error;
        this.activePdfFile.isParsing = false;
      }
    },
    
    // 设置PDF页码
    setPdfPage(page) {
      this.pdfPage = page;
    },
    
    // 增加PDF页码
    nextPdfPage() {
      if (this.activePdfFile && this.pdfPage < this.activePdfFile.pages) {
        this.pdfPage++;
      }
    },
    
    // 减少PDF页码
    prevPdfPage() {
      if (this.pdfPage > 1) {
        this.pdfPage--;
      }
    },
    
    // 设置PDF缩放比例
    setPdfZoom(zoom) {
      // 限制缩放范围在0.5到2.0之间
      this.pdfZoom = Math.max(0.5, Math.min(2.0, zoom));
    },
    
    // 切换深色模式
    toggleDarkMode() {
      this.isDarkMode = !this.isDarkMode;
      this.updateThemeClass();
    },
    
    // 更新主题类
    updateThemeClass() {
      const html = document.documentElement;
      if (this.isDarkMode) {
        html.classList.add('dark');
      } else {
        html.classList.remove('dark');
      }
    },
    
    // 切换侧边栏折叠状态
    toggleSidebar() {
      this.sidebarCollapsed = !this.sidebarCollapsed;
    },
    
    // 切换移动端菜单
    toggleMobileMenu() {
      this.mobileMenuOpen = !this.mobileMenuOpen;
    },
    
    // 设置加载状态
    setLoading(loading) {
      this.isLoading = loading;
    },
    
    // 设置API连接状态
    setApiStatus(status) {
      this.apiStatus = status;
    },
    
    // 设置会话ID
    setSessionId(sessionId) {
      this.currentSessionId = sessionId;
      this.clearChatMessages(); // 切换会话时清空聊天记录
    },
  },
});