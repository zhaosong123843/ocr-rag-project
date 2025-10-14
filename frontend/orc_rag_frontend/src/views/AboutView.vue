<template>
  <div class="app-container">

    <!-- 主要内容区域 -->
    <div class="main-content">
      <!-- 左侧：AI Assistant 区域 -->
      <div class="ai-assistant-panel">
        <!-- 标题栏 -->
        <div class="panel-header">
          <div>
            <h2 class="assistant-title">AI Assistant</h2>
            <p class="assistant-subtitle">Powered by RAG Technology</p>
          </div>
          <div class="header-actions">
            <button class="clear-button" @click="clearChat">Clear</button>
          </div>
        </div>

        <!-- 聊天对话区域 -->
        <div class="chat-messages" ref="chatMessagesContainer">
          <!-- 使用v-for渲染消息列表 -->
          <div v-for="(message, index) in formattedMessages" :key="index"
            :class="['message', message.type === 'ai' ? 'ai-message' : 'user-message']">
            <div class="message-bubble">
              <p v-if="message.type !== 'ai'">
                {{ message.content }}
              </p>
              <div v-else v-html="message.formattedContent"></div>
            </div>
          </div>
        </div>

        <!-- 输入框区域 -->
        <div class="input-area">
          <input type="text" class="message-input" placeholder="Ask a question..." v-model="messageText"
            @keyup.enter="sendMessage">
          <button class="send-button" @click="sendMessage">
            <svg class="send-icon" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M17 2L9 10L17 2M17 2L12 16L9 10L3 6L17 2Z"></path>
            </svg>
          </button>
        </div>
      </div>

      <!-- 右侧：Document 区域 -->
      <div class="document-panel">
        <!-- 标题栏 -->
        <div class="panel-header">
          <h2>Document</h2>
          <div class="header-actions">
            <button class="refresh-button" @click="refreshDocument">
              <!-- <svg class="refresh-icon" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M2 2v4h4M14 14v-4h-4M2 14A10 10 0 0 1 12 4m0 12A10 10 0 0 1 2 6"></path>
              </svg> -->
              <span>重置</span>
            </button>
          </div>
        </div>

        <!-- 文件选择区域 -->
        <div class="file-selector">
          <!-- 统一的按钮组，无论是否上传文件都显示 -->
          <div class="file-upload-container">
            <div class="button-group">
              <!-- upload按钮 -->
              <div style="display: flex; align-items: center; justify-content: center;">
                <button class="upload-button" @click="handleFileUpload" :disabled="isUploading">
                  <svg class="upload-icon" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5">
                    <path d="M8 2v6M5 5l3-3 3 3M1 10a5 5 0 0 1 5-5h4a5 5 0 0 1 5 5v2a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2v-2z">
                    </path>
                  </svg>
                  <span>上传文件</span>
                </button>
                <!-- 上传进度圈 -->
                <div class="progress-circle-container">
                  <svg class="progress-circle" viewBox="0 0 30 30" v-if="isUploading">
                    <circle class="progress-circle-bg" cx="15" cy="15" r="13" fill="none" stroke="#333"
                      stroke-width="2" />
                    <circle class="progress-circle-fill" cx="15" cy="15" r="13" fill="none" stroke="#4ade80"
                      stroke-width="2" :stroke-dasharray="81.68"
                      :stroke-dashoffset="81.68 - (uploadProgress / 100) * 81.68" stroke-linecap="round"
                      transform="rotate(-90 15 15)" />
                    <text class="progress-circle-text" x="15" y="18" text-anchor="middle" font-size="6">{{
                      Math.round(uploadProgress) }}%</text>
                  </svg>
                  <svg class="progress-success" viewBox="0 0 30 30" v-else-if="!isUploading && uploadProgress >= 100">
                    <circle cx="15" cy="15" r="13" fill="none" stroke="#22c55e" stroke-width="2" />
                    <path d="M9 15l3 3l6-6" stroke="#22c55e" stroke-width="2" stroke-linecap="round"
                      stroke-linejoin="round" />
                  </svg>
                </div>
              </div>


              <!-- parser按钮 -->
              <div class="parser-button-container">
                <button class="parser-button" @click="handleParse"
                  :disabled="!uploadedFile || isUploading || isParsing">
                  <svg class="parser-icon" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5">
                    <path d="M2 8h12M2 12h12M2 4h12M7 2v12"></path>
                  </svg>
                  <span>解析文档</span>
                </button>

                <!-- 解析进度圈 -->
                <div class="progress-circle-container">
                  <svg class="progress-circle" viewBox="0 0 30 30" v-if="isParsing">
                    <circle class="progress-circle-bg" cx="15" cy="15" r="13" fill="none" stroke="#333"
                      stroke-width="2" />
                    <circle class="progress-circle-fill" cx="15" cy="15" r="13" fill="none" stroke="#3b82f6"
                      stroke-width="2" :stroke-dasharray="81.68"
                      :stroke-dashoffset="81.68 - (parseProgress / 100) * 81.68" stroke-linecap="round"
                      transform="rotate(-90 15 15)" />
                    <text class="progress-circle-text" x="15" y="18" text-anchor="middle" font-size="6">{{
                      Math.round(parseProgress) }}%</text>
                  </svg>
                  <svg class="progress-success" viewBox="0 0 30 30" v-else-if="!isParsing && parseProgress >= 100">
                    <circle cx="15" cy="15" r="13" fill="none" stroke="#22c55e" stroke-width="2" />
                    <path d="M9 15l3 3l6-6" stroke="#22c55e" stroke-width="2" stroke-linecap="round"
                      stroke-linejoin="round" />
                  </svg>
                </div>
              </div>
            </div>
          </div>

        </div>

        <!-- 文件选择下拉框 -->
        <div class="file-selector-dropdown">
          <select v-model="selectedFile" class="file-dropdown">
            <option value="" disabled>请选择文件</option>
            <option v-for="file in availableFiles" :key="file.value" :value="file.value">
              {{ file.displayName }}
            </option>
          </select>
          <button class="load-button" @click="loadSelectedFile" :disabled="!selectedFile">
            加载
          </button>
        </div>

        <!-- 文件名和标签切换在同一行 -->
        <div class="file-tabs-container">
          <!-- 标签切换 -->
          <div class="tabs">
            <div class="tab-buttons">
              <button class="tab" :class="{ active: activeTab === 'original' }" @click="switchTab('original')">
                Original
              </button>
              <button class="tab" :class="{ active: activeTab === 'parsed' }" @click="switchTab('parsed')">
                Parsed
              </button>
            </div>
            <div class="tab-file-name-container">
              <!-- 文件名显示在按钮最右侧 -->
              <div v-if="uploadedFile" class="tabs-file-name">
                {{ uploadedFile.name }}
              </div>
            </div>
          </div>
        </div>

        <!-- 文档预览区域 - 用于呈现后端传来的PNG图片 -->
        <div class="document-preview">
          <!-- 显示通过加载按钮获取的图片 -->
          <div class="preview-image" v-if="currentImageUrl">
            <img :src="currentImageUrl"
              :style="{ transform: `scale(${zoomLevel / 100})` }"
              :alt="`${uploadedFile?.name || 'Loaded Document'} - Page ${currentPage}`"
              @error="handleImageError" />
          </div>
          
          <!-- 显示通过上传解析获取的图片 -->
          <div class="preview-image" v-else-if="uploadedFile && uploadedFile.fileId && parseProgress >= 100">
            <img :src="getPdfPageImageUrl(uploadedFile.fileId, currentPage, activeTab)"
              :style="{ transform: `scale(${zoomLevel / 100})` }"
              :alt="`Page ${currentPage} (${activeTab === 'original' ? 'Original' : 'Parsed'})`"
              @error="handleImageError" />
          </div>
          
          <div v-else class="preview-placeholder">
            <p>请先上传并解析PDF文件，或从文件列表加载文件</p>
          </div>
        </div>

        <!-- 底部状态栏 - 固定在右侧栏底部 -->
        <div class="status-bar" v-if="uploadedFile">
          <div class="page-controls">
            <button class="page-button" :disabled="currentPage <= 1" @click="changePage(-1)">
              上一页
            </button>
            <div class="page-info">
              Page {{ currentPage }} of {{ uploadedFile.pages || 1 }}
            </div>
            <button class="page-button" :disabled="!uploadedFile.pages || currentPage >= uploadedFile.pages"
              @click="changePage(1)">
              下一页
            </button>
          </div>
          <div class="zoom-controls">
            <button class="zoom-button" :disabled="zoomLevel <= 50" @click="changeZoom(-10)">
              -
            </button>
            <span class="zoom-level">{{ zoomLevel }}%</span>
            <button class="zoom-button" :disabled="zoomLevel >= 200" @click="changeZoom(10)">
              +
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, computed } from 'vue';
import { 
  uploadPdf, 
  startParse, 
  getParseStatus, 
  getPdfPageUrl, 
  processChatStream, 
  buildIndex, 
  getPdfFiles, 
  getPdfPageByFileName,
  getPdfPages
 } from '../services/api.js';
import MarkdownIt from 'markdown-it';


// 创建markdown-it实例
const md = new MarkdownIt({
  html: true,      // 允许HTML标签
  linkify: true,   // 自动识别链接
  typographer: true // 自动转换一些排版符号
});

// 计算属性：获取格式化后的消息
const formattedMessages = computed(() => {
  return messages.value.map(msg => {
    if (msg.type === 'ai') {
      // 预处理AI消息中的图片URL，将相对路径转换为绝对URL
      const processedContent = msg.content.replace(
        /!\[(.*?)\]\((\/api\/.*?)\)/g, 
        (match, alt, url) => `![${alt}](http://localhost:8001${url})`
      );
      // 对预处理后的内容进行Markdown格式化
      const renderedContent = md.render(processedContent);
      // 为图片添加内联样式
      const styledContent = renderedContent.replace(
        /<img/g, 
        '<img style="max-width: 100%; max-height: 300px; height: auto; border-radius: 4px; margin: 8px 0; object-fit: contain; border: 1px solid rgba(255, 255, 255, 0.1);"'
      );
      return {
        ...msg,
        formattedContent: styledContent
      };
    }
    return {
      ...msg,
      formattedContent: msg.content
    };
  });
});

// 响应式数据
const messageText = ref('');
const chatMessagesContainer = ref(null);
const messages = ref([
  {
    type: 'ai',
    content: '你好，我是你的AI智能助手，请问有什么需要帮忙的？.'
  }
]);
const activeTab = ref('original');
const uploadedFile = ref(null); // 存储上传的文件信息
const uploadProgress = ref(0); // 上传进度
const isUploading = ref(false); // 是否正在上传
const isParsing = ref(false); // 是否正在解析
const parseProgress = ref(0); // 解析进度
const currentPage = ref(1); // 当前页码
const zoomLevel = ref(100); // 缩放级别 (百分比)
const availableFiles = ref([]); // 后端传入的文件名列表
const selectedFile = ref(''); // 下拉框选中的文件名
const currentImageUrl = ref(''); // 当前显示的图片URL

// 切换标签
async function switchTab(tab) {
  activeTab.value = tab;
  // 标签切换后重新加载当前页面
  currentPage.value = 1;
  
  // 如果当前有加载的文件，重新获取对应类型的图片
  if (selectedFile.value && currentImageUrl.value) {
    try {
      const imageUrl = await getPdfPageByFileName(selectedFile.value, currentPage.value, activeTab.value);
      currentImageUrl.value = imageUrl;
      console.log('切换标签后重新加载图片:', imageUrl);
    } catch (error) {
      console.error('切换标签后重新加载图片失败:', error);
      // 如果解析后的图片不存在，清空当前图片URL
      if (activeTab.value === 'parsed') {
        currentImageUrl.value = '';
        alert('解析后的文档图片尚未生成，请等待解析完成后再查看。');
      }
    }
  }
}

// 组件内的辅助函数：获取PDF页面URL
function getPdfPageImageUrl(fileId, page, type = 'original') {
  return getPdfPageUrl(fileId, page, type);
}

// 加载选中的文件
async function loadSelectedFile() {
  // selectedFile.value为file_id
  if (!selectedFile.value) {
    alert('请选择一个文件');
    return;
  }
  
  console.log('加载文件:', selectedFile.value);
  
  try {
    // 调用后端API加载选中的文件的第一页
    const imageUrl = await getPdfPageByFileName(selectedFile.value, 1, activeTab.value);
    
    // 获取PDF文件总页数
    let totalPages = 1;
    try {
      const pagesResponse = await getPdfPages(selectedFile.value);
      totalPages = pagesResponse.pages || 1;
      console.log('获取到PDF总页数:', totalPages);
    } catch (pagesError) {
      console.warn('获取PDF页数失败，使用默认值1:', pagesError);
    }
    
    // 查找选中的文件信息以获取原始文件名
    const selectedFileInfo = availableFiles.value.find(file => file.value === selectedFile.value);
    const displayName = selectedFileInfo ? selectedFileInfo.displayName : selectedFile.value;
    
    // 更新当前文件信息
    uploadedFile.value = {
      name: displayName,        // 显示给用户的原始文件名
      fileId: selectedFile.value, // 实际使用的随机文件名作为文件ID
      pages: totalPages // 从后端获取的实际页数
    };
    
    // 存储图片URL用于渲染
    currentImageUrl.value = imageUrl;
    
    console.log('当前文件信息:', uploadedFile.value);

    isParsing.value = false;
    
  } catch (error) {
    console.error('加载文件失败:', error);
    alert('加载文件失败，请重试');
  }
}

// 加载文件列表
async function loadFileList() {
  try {
    const response = await getPdfFiles();
    // 后端返回格式：{"files": [{"file_name": "原始文件名", "random_name": "随机文件名"}, ...]}
    // 我们需要将文件列表转换为适合下拉框的格式
    availableFiles.value = response.files.map(file => ({
      displayName: file.file_name, // 显示给用户的原始文件名
      value: file.random_name      // 实际使用的随机文件名
    })) || [];
    console.log('获取到的文件列表:', availableFiles.value);
  } catch (error) {
    console.error('获取文件列表失败:', error);
    availableFiles.value = [];
  }
}

// 清空聊天记录
function clearChat() {
  messages.value = [
    {
      type: 'ai',
      content: 'Hello! I\'m your AI Assistant. You can chat directly, and if you upload a PDF I can answer with document-grounded citations.'
    }
  ];
  nextTick(() => {
    if (chatMessagesContainer.value) {
      chatMessagesContainer.value.scrollTop = chatMessagesContainer.value.scrollHeight;
    }
  });
}

// 改变页码
async function changePage(delta) {
  const newPage = currentPage.value + delta;
  if (newPage >= 1 && (!uploadedFile.value.pages || newPage <= uploadedFile.value.pages)) {
    // 更新当前页码
    currentPage.value = newPage;
    
    // 如果有选中的文件，加载新页面的图片
    if (selectedFile.value) {
      try {
        const imageUrl = await getPdfPageByFileName(selectedFile.value, newPage, activeTab.value);
        currentImageUrl.value = imageUrl;
        console.log('加载第', newPage, '页图片成功');
      } catch (error) {
        console.error('加载第', newPage, '页图片失败:', error);
        // 如果加载失败，恢复原来的页码
        currentPage.value = currentPage.value - delta;
        alert('加载页面失败，请重试');
      }
    }
  }
}

// 改变缩放级别
function changeZoom(delta) {
  const newZoom = zoomLevel.value + delta;
  if (newZoom >= 50 && newZoom <= 200) {
    zoomLevel.value = newZoom;
  }
}

// 处理图片加载错误
function handleImageError(event) {
  // 如果是parsed类型的图片加载失败，可能是因为文档还未解析完成
  if (activeTab.value === 'parsed') {
    event.target.src = '';
    alert('解析后的文档图片尚未生成，请等待解析完成后再查看。');
  } else {
    // 其他类型的错误处理
    console.error('图片加载失败:', event);
  }
}

// 处理AI消息中的图片加载错误
function handleAIImageError(event) {
  // 确保是图片元素的错误
  if (event.target.tagName === 'IMG') {
    // 替换为占位图或者显示友好的错误信息
    event.target.src = 'data:image/svg+xml;charset=utf-8,%3Csvg xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22 width%3D%22200%22 height%3D%22120%22 viewBox%3D%220 0 200 120%22%3E%3Crect width%3D%22200%22 height%3D%22120%22 fill%3D%22%23f3f4f6%22%2F%3E%3Ctext x%3D%22100%22 y%3D%2265%22 font-family%3D%22Arial%22 font-size%3D%2214%22 text-anchor%3D%22middle%22 fill%3D%22%236b7280%22%3E图片加载失败%3C%2Ftext%3E%3C%2Fsvg%3E';
    event.target.alt = '图片加载失败';
  }
}

// 发送消息
function sendMessage() {
  // 防止发送空消息
  if (!messageText.value.trim()) return;

  // 添加用户消息
  messages.value.push({
    type: 'user',
    content: messageText.value.trim()
  });

  // 清空输入框
  messageText.value = '';

  // 滚动到底部
  nextTick(() => {
    if (chatMessagesContainer.value) {
      chatMessagesContainer.value.scrollTop = chatMessagesContainer.value.scrollHeight;
    }
  });

  // 添加AI消息容器
  const aiMessageIndex = messages.value.length;
  messages.value.push({
    type: 'ai',
    content: ''
  });

  // 滚动到底部
  nextTick(() => {
    if (chatMessagesContainer.value) {
      chatMessagesContainer.value.scrollTop = chatMessagesContainer.value.scrollHeight;
    }
  });

  // 调用聊天API
  processChatStream(
    messages.value[aiMessageIndex - 1].content,
    // onToken回调：处理单个token
    (token) => {
      messages.value[aiMessageIndex].content += token;
      // 滚动到底部
      nextTick(() => {
        if (chatMessagesContainer.value) {
          chatMessagesContainer.value.scrollTop = chatMessagesContainer.value.scrollHeight;
        }
      });
    },
    // onCitation回调：处理引用
    (citation) => {
      console.log('收到引用:', citation);
      // 这里可以根据需要处理引用，例如显示引用标记
    },
    // onDone回调：处理完成事件
    (doneData) => {
      console.log('聊天完成:', doneData);
    },
    // onError回调：处理错误
    (errorMessage) => {
      console.error('聊天错误:', errorMessage);
      messages.value[aiMessageIndex].content = `发生错误：${errorMessage}`;
      // 滚动到底部
      nextTick(() => {
        if (chatMessagesContainer.value) {
          chatMessagesContainer.value.scrollTop = chatMessagesContainer.value.scrollHeight;
        }
      });
    },
    // pdfFileId：如果有上传的文件，提供文件id
    uploadedFile.value?.fileId || null,
    // sessionId：使用默认会话ID
    'default'
  );
}

// 处理文件上传
async function handleFileUpload() {
  // 创建隐藏的文件输入元素
  const fileInput = document.createElement('input');
  fileInput.type = 'file';
  fileInput.accept = '.pdf'; // 仅接受PDF文件

  fileInput.onchange = async (event) => {
    if (event.target.files && event.target.files[0]) {
      const file = event.target.files[0];

      // 校验文件类型是否为PDF
      const fileExtension = file.name.split('.').pop().toLowerCase();
      const fileType = file.type;

      if (fileExtension !== 'pdf' && fileType !== 'application/pdf') {
        alert('只能上传PDF格式的文档，请选择正确的文件类型。');
        return;
      }

      // 检查文件名冲突并生成唯一文件名
      const uniqueFileName = generateUniqueFileName(file.name, availableFiles.value);
      
      // 创建重命名后的文件对象
      const renamedFile = new File([file], uniqueFileName, { type: file.type });
      
      uploadedFile.value = renamedFile;
      isUploading.value = true;
      uploadProgress.value = 0;

      try {
        // 使用模拟进度的方式展示上传过程
        // simulateUploadProgress();

        // 调用后端API上传文件
        const response = await uploadPdf(renamedFile, true);

        // 上传成功后，更新uploadedFile为后端返回的完整信息
        // 添加详细日志以便调试
        console.log('上传成功前的uploadedFile:', uploadedFile.value);

        // 保存文件名称，确保不会丢失
        const fileName = uploadedFile.value?.name || file.name;

        // 更新uploadedFile为包含后端返回信息的对象
        uploadedFile.value = {
          ...file,
          name: fileName, // 确保名称被保留
          fileId: response.fileId,
          pages: response.pages
        };

        console.log('上传成功后的uploadedFile:', uploadedFile.value);

        // 模拟进度完成
        uploadProgress.value = 100;
        isUploading.value = false;
      } catch (error) {
        // 处理上传错误
        console.error('文件上传失败:', error);
        // 重置状态
        isUploading.value = false;
        uploadProgress.value = 0;
        // 可以在这里添加错误提示
        alert('文件上传失败，请重试');
      }
    }
  };

  fileInput.click();
}

// 处理解析
async function handleParse() {
  if (!uploadedFile.value || !uploadedFile.value.fileId) {
    alert('请先上传文件');
    return;
  }

  isParsing.value = true;
  parseProgress.value = 0;

  try {
    // 调用后端API开始解析
    const response = await startParse(uploadedFile.value.fileId);
    console.log('开始解析任务:', response);

    // 开始轮询解析进度
    pollParseStatus();
  } catch (error) {
    console.error('解析失败:', error);
    isParsing.value = false;
    parseProgress.value = 0;
    alert('解析失败，请重试');
  }
}

// 轮询解析进度
function pollParseStatus() {
  const interval = setInterval(async () => {
    try {
      console.log('当前文件ID:', uploadedFile.value.fileId);
      // 调用后端API查询解析状态
      const status = await getParseStatus(uploadedFile.value.fileId);

      // 更新解析进度
      if (status.progress !== undefined) {
        parseProgress.value = status.progress;
      }

      // 检查解析状态
      if (status.status === 'ready') {
        // 解析完成
        parseProgress.value = 100;
        clearInterval(interval);
        isParsing.value = false;
        // 弹窗显示解析完成
        alert('解析完成');
        console.log('解析完成');
        
        // 自动触发索引构建
        try {
          console.log('开始构建索引...');
          const indexResult = await buildIndex(uploadedFile.value.fileId);
          console.log('索引构建成功:', indexResult);
          // 弹窗显示索引构建完成
          alert('索引构建完成');  
        } catch (indexError) {
          console.error('索引构建失败:', indexError);
          // 索引构建失败不影响主流程
        }

        // 可以在这里添加成功提示或其他逻辑

        // 切换到解析后的标签页
        activeTab.value = 'parsed';
      } else if (status.status === 'error') {
        // 解析错误
        clearInterval(interval);
        isParsing.value = false;
        parseProgress.value = 0;
        console.error('解析过程中出错');
        alert('解析失败，请重试');
      }
    } catch (error) {
      console.error('查询解析状态失败:', error);
      // 继续轮询，直到达到最大重试次数或用户取消
    }
  }, 5000); // 每秒查询一次
}

// 生成不重复的文件名
function generateUniqueFileName(originalName, existingFiles) {
  // 提取文件名和扩展名
  const baseName = originalName.replace(/\.pdf$/i, '');
  const extension = '.pdf';
  
  // 检查是否存在同名文件 - 现在existingFiles是对象数组，需要提取displayName
  const existingNames = existingFiles.map(file => 
    typeof file === 'string' ? file.toLowerCase() : file.displayName.toLowerCase()
  );
  
  if (!existingNames.includes(originalName.toLowerCase())) {
    return originalName;
  }
  
  // 查找已存在的编号
  const pattern = new RegExp(`^${baseName.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\((\\d+)\\)\\.pdf$`, 'i');
  let maxNumber = 0;
  
  existingNames.forEach(name => {
    const match = name.match(pattern);
    if (match) {
      const number = parseInt(match[1], 10);
      if (number > maxNumber) {
        maxNumber = number;
      }
    }
  });
  
  // 生成新的文件名
  return `${baseName}(${maxNumber + 1})${extension}`;
}

// 刷新Document区域
function refreshDocument() {
  uploadedFile.value = null;
  uploadProgress.value = 0;
  parseProgress.value = 0;
  isUploading.value = false;
  isParsing.value = false;
  activeTab.value = 'original';
  
  // 重置文件选择和图片预览相关状态
  selectedFile.value = '';
  currentImageUrl.value = '';
  currentPage.value = 1;
  
  console.log('文档区域已刷新，重置所有状态');
}

// 组件挂载后滚动到底部并加载文件列表
onMounted(() => {
  nextTick(() => {
    if (chatMessagesContainer.value) {
      chatMessagesContainer.value.scrollTop = chatMessagesContainer.value.scrollHeight;
    }
  });
  
  // 加载文件列表
  loadFileList();
});
</script>

<style scoped>
/* 全局样式 */
* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

.app-container {
  width: 100%;
  height: 100%;
  background-color: #121212;
  color: #ffffff;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}



/* 主内容区域 */
.main-content {
  flex: 1;
  display: flex;
  overflow: hidden;
}

/* 左侧AI助手面板 */
.ai-assistant-panel {
  width: 60%;
  display: flex;
  flex-direction: column;
  border-right: 1px solid #333;
  background-color: #1a1a1a;
}

/* 右侧文档面板 */
.document-panel {
  width: 40%;
  display: flex;
  flex-direction: column;
  background-color: #1a1a1a;
}

/* 面板标题栏 */
.panel-header {
  padding: 12px 16px;
  background-color: #1a1a1a;
  border-bottom: 1px solid #333;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.assistant-title {
  font-size: 18px;
  font-weight: 600;
  color: #ffffff;
  margin-bottom: 2px;
}

.assistant-subtitle {
  font-size: 11px;
  color: #cccccc;
  margin: 0;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.clear-button {
  padding: 4px 8px;
  background-color: transparent;
  border: 1px solid #444;
  border-radius: 4px;
  color: #cccccc;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.clear-button:hover {
  border-color: #666;
  color: #ffffff;
}

.refresh-button {
  padding: 6px;
  background-color: transparent;
  border: 1px solid #444;
  border-radius: 4px;
  color: #cccccc;
  cursor: pointer;
  transition: all 0.2s;
}

.refresh-button:hover {
  border-color: #666;
  color: #ffffff;
}

.refresh-icon {
  width: 12px;
  height: 12px;
}

/* 聊天消息区域 */
.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  background-color: #1a1a1a;
  min-height: 0;
}

/* 消息样式 */
.message {
  margin-bottom: 16px;
  display: flex;
  align-items: flex-start;
}

.ai-message {
  justify-content: flex-start;
}

.user-message {
  justify-content: flex-end;
}

.message-bubble {
  max-width: 70%;
  padding: 12px 16px;
  border-radius: 18px;
  font-size: 14px;
  line-height: 1.5;
  word-wrap: break-word;
  position: relative;
}

.ai-message .message-bubble {
  background-color: #1e3a8a;
  color: #ffffff;
  border-bottom-left-radius: 4px;
}

.user-message .message-bubble {
  background-color: #4ade80;
  color: #000000;
  border-bottom-right-radius: 4px;
}

/* 聊天消息中的图片样式 */
.ai-message .message-bubble img {
  max-width: 100% !important;
  max-height: 300px !important;
  height: auto !important;
  border-radius: 4px !important;
  margin: 8px 0 !important;
  object-fit: contain !important;
  border: 1px solid rgba(255, 255, 255, 0.1) !important;
}

.ai-message .message-bubble img:hover {
  border-color: rgba(255, 255, 255, 0.3) !important;
}

/* 消息箭头效果 */
.ai-message .message-bubble::before {
  content: '';
  position: absolute;
  bottom: 0;
  left: -8px;
  width: 0;
  height: 0;
  border-style: solid;
  border-width: 8px 8px 0 0;
  border-color: #1e3a8a transparent transparent transparent;
}

.user-message .message-bubble::before {
  content: '';
  position: absolute;
  bottom: 0;
  right: -8px;
  width: 0;
  height: 0;
  border-style: solid;
  border-width: 8px 0 0 8px;
  border-color: #4ade80 transparent transparent transparent;
}

.reference-container {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}

.reference-image {
  width: 100%;
  max-height: 120px;
  object-fit: contain;
  border: 1px solid #333;
  border-radius: 4px;
}

.chart-container {
  margin-top: 10px;
  padding: 10px;
  background-color: #1a1a1a;
  border: 1px solid #333;
  border-radius: 4px;
}

.architecture-chart {
  width: 100%;
  height: auto;
  max-height: 150px;
}

/* 输入区域 */
.input-area {
  padding: 12px 16px;
  background-color: #1a1a1a;
  border-top: 1px solid #333;
  display: flex;
  gap: 8px;
  align-items: center;
}

.message-input {
  flex: 1;
  padding: 8px 12px;
  background-color: #2a2a2a;
  border: 1px solid #444;
  border-radius: 20px;
  color: #ffffff;
  font-size: 14px;
  outline: none;
}

.message-input:focus {
  border-color: #00bfff;
}

.message-input::placeholder {
  color: #888;
}

.send-button {
  padding: 8px 12px;
  background-color: #00bfff;
  border: none;
  border-radius: 50%;
  color: #ffffff;
  cursor: pointer;
  transition: background-color 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.send-button:hover {
  background-color: #00a0e9;
}

.send-icon {
  width: 16px;
  height: 16px;
}

/* 文件选择器 */
.file-selector {
  padding: 12px 16px;
  background-color: #1a1a1a;
  border-bottom: 1px solid #333;
  display: flex;
  justify-content: space-between;
  align-items: center;
  min-height: 80px;
}

.file-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 8px;
  background-color: #2d2d2d;
  border-radius: 4px;
  max-width: 60%;
}

.file-name {
  font-size: 14px;
  color: #ffffff;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
  margin-right: 8px;
}

.close-file-button {
  padding: 2px;
  background-color: transparent;
  border: none;
  color: #666;
  cursor: pointer;
  transition: color 0.2s;
}

.close-file-button:hover {
  color: #ffffff;
}

.upload-button {
  padding: 6px 16px;
  background-color: #4ade80;
  /* 浅绿色 */
  border: none;
  border-radius: 4px;
  color: #000000;
  cursor: pointer;
  transition: background-color 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  font-size: 12px;
  min-width: 400px;
  text-align: center;
}

.upload-button:hover {
  background-color: #22c55e;
}

.file-upload-container {
  width: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
}

.button-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
  max-width: 500px;
}

.parser-button {
  padding: 6px 16px;
  background-color: #3b82f6;
  /* 蓝色 */
  border: none;
  border-radius: 4px;
  color: #ffffff;
  cursor: pointer;
  transition: background-color 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  font-size: 12px;
  min-width: 400px;
  text-align: center;
}

.parser-button:hover:not(:disabled) {
  background-color: #2563eb;
}

.parser-button:disabled {
  background-color: #444;
  cursor: not-allowed;
  opacity: 0.6;
}

.parser-button-container {
  display: flex;
  justify-content: center;
  margin-bottom: 8px;
}

.parser-icon {
  width: 12px;
  height: 12px;
}

.uploaded-file-container {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.progress-container {
  width: 100%;
  position: relative;
}

.progress-bar {
  width: 100%;
  height: 4px;
  background-color: #333;
  border-radius: 2px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background-color: #4ade80;
  transition: width 0.3s ease;
  border-radius: 2px;
}

.progress-fill.upload-progress {
  background-color: #4ade80;
  /* 上传进度条绿色 */
}

.progress-fill.parse-progress {
  background-color: #3b82f6;
  /* 解析进度条蓝色 */
}

.progress-text {
  position: absolute;
  right: 0;
  top: -16px;
  font-size: 11px;
  color: #4ade80;
}

.upload-icon {
  width: 12px;
  height: 12px;
}

/* 文件名和标签切换容器 */
.file-tabs-container {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  margin-top: 16px;
  margin-bottom: 16px;
}

/* 标签切换 */
.tabs {
  display: flex;
  background-color: #1a1a1a;
  border-bottom: 1px solid #333;
  flex: 1;
  justify-content: space-between;
  align-items: center;
}

/* 标签按钮组 */
.tab-buttons {
  display: flex;
}

/* 标签文件名容器 */
.tab-file-name-container {
  display: flex;
  align-items: center;
}

/* 标签右侧的文件名显示 */
.tabs-file-name {
  display: flex;
  align-items: center;
  margin-left: 16px;
  padding: 4px 8px;
  background-color: #2d2d2d;
  border-radius: 4px;
  font-size: 14px;
  color: #ffffff;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 200px;
}

.tab {
  padding: 10px 16px;
  border: none;
  color: #888888;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
  position: relative;
  background-color: #2a2a2a;
}

.tab:hover {
  background-color: #333333;
}

.tab.active {
  color: #ffffff;
  background-color: #007acc;
}

.tab.active::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  width: 100%;
  height: 2px;
  background-color: #007acc;
}

/* 文档预览区域 */
.document-preview {
  flex: 1;
  display: flex;
  overflow: auto;
  background-color: #1a1a1a;
  min-height: 600px;
  justify-content: center;
  align-items: center;
}

.document-preview img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}

.text-content {
  width: 50%;
  padding: 16px;
  overflow-y: auto;
  border-right: 1px solid #333;
}

.text-content h3 {
  font-size: 14px;
  font-weight: 600;
  color: #ff69b4;
  margin-bottom: 10px;
  margin-top: 16px;
}

.text-content p {
  font-size: 13px;
  color: #ffffff;
  line-height: 1.5;
  margin-bottom: 10px;
}

.text-content ul {
  list-style-type: disc;
  padding-left: 20px;
  margin-bottom: 10px;
}

.text-content li {
  font-size: 13px;
  color: #ffffff;
  line-height: 1.5;
  margin-bottom: 5px;
}

.image-preview {
  width: 50%;
  padding: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.preview-image {
  width: 100%;
  height: 100%;
  max-height: 600px;
  border: 1px solid #333;
  border-radius: 4px;
  overflow: auto;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #2a2a2a;
}

.preview-svg {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

/* 上传文件信息样式 */
.uploaded-file-info {
  margin-top: 8px;
}

/* 进度圈样式 */
.progress-circle-container {
  margin-left: 8px;
  display: inline-block;
}

.progress-circle {
  width: 16px;
  height: 16px;
  transform: rotate(-90deg);
}

.progress-circle-bg {
  fill: none;
  stroke: #333;
  stroke-width: 2;
}

.progress-circle-fill {
  fill: none;
  stroke-width: 2;
  transition: stroke-dashoffset 0.3s ease;
  stroke-linecap: round;
}

.progress-circle-text {
  fill: #ffffff;
  font-size: 6px;
  dominant-baseline: middle;
  text-anchor: middle;
}

.progress-success {
  width: 16px;
  height: 16px;
}

/* 底部状态栏 */
.status-bar {
  padding: 8px 16px;
  background-color: #0a0a0a;
  border-top: 1px solid #333;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 11px;
  color: #888;
}

.zoom-controls {
  display: flex;
  align-items: center;
  gap: 8px;
}

.zoom-button {
  width: 20px;
  height: 20px;
  background-color: #2a2a2a;
  border: 1px solid #444;
  border-radius: 4px;
  color: #cccccc;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.zoom-button:hover {
  background-color: #3a3a3a;
  border-color: #666;
}

.zoom-level {
  min-width: 40px;
  text-align: center;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .main-content {
    flex-direction: column;
  }

  .ai-assistant-panel,
  .document-panel {
    width: 100%;
    height: 50%;
  }

  .ai-assistant-panel {
    border-right: none;
    border-bottom: 1px solid #333;
  }

  .document-preview {
    flex-direction: column;
  }

  .text-content,
  .image-preview {
    width: 100%;
  }

  .text-content {
    border-right: none;
    border-bottom: 1px solid #333;
    height: 50%;
  }

  .image-preview {
    height: 50%;
  }
}

/* 文件选择下拉框样式 */
.file-selector-dropdown {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background-color: #1a1a1a;
  border-bottom: 1px solid #333;
}

.file-dropdown {
  flex: 1;
  padding: 8px 12px;
  background-color: #2a2a2a;
  border: 1px solid #444;
  border-radius: 4px;
  color: #ffffff;
  font-size: 14px;
  outline: none;
  cursor: pointer;
  transition: border-color 0.2s;
}

.file-dropdown:focus {
  border-color: #00bfff;
}

.file-dropdown option {
  background-color: #2a2a2a;
  color: #ffffff;
}

.file-dropdown option:disabled {
  color: #888;
}

.load-button {
  padding: 8px 16px;
  background-color: #3b82f6;
  border: none;
  border-radius: 4px;
  color: #ffffff;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background-color 0.2s;
  white-space: nowrap;
}

.load-button:hover:not(:disabled) {
  background-color: #2563eb;
}

.load-button:disabled {
  background-color: #444;
  color: #888;
  cursor: not-allowed;
  opacity: 0.6;
}
</style>