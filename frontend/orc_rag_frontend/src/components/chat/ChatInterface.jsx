// 聊天界面组件
import { ref, computed, onMounted } from 'vue';
import { useAppStore } from '@/store';
import { processChatStream } from '@/services/api';
import MarkdownIt from 'markdown-it';
import { Paperclip, Warning, Link } from '@element-plus/icons-vue';
import { ElButton, ElInput, ElAvatar, ElMessage } from 'element-plus';
import ApiImageRenderer from '@/components/ApiImageRenderer.vue';

// 初始化Markdown解析器
const md = new MarkdownIt({
  html: true,
  linkify: true,
  typographer: true,
  breaks: true
});

// 自定义渲染器处理引用
const defaultLinkOpenRender = md.renderer.rules.link_open || function(tokens, idx, options, env, self) {
  return self.renderToken(tokens, idx, options);
};

md.renderer.rules.link_open = function(tokens, idx, options, env, self) {
  const token = tokens[idx];
  // 为所有链接添加target="_blank"
  token.attrSet('target', '_blank');
  token.attrSet('rel', 'noopener noreferrer');
  
  return defaultLinkOpenRender(tokens, idx, options, env, self);
};

export default {
  name: 'ChatInterface',
  setup() {
    const store = useAppStore();
    const userMessage = ref('');
    const isTyping = ref(false);
    const chatContainer = ref(null);

    // 计算属性
    const chatMessages = computed(() => store.getChatMessages);
    const activePdfFile = computed(() => store.getActivePdfFile);

    // 滚动到底部
    const scrollToBottom = () => {
      if (chatContainer.value) {
        setTimeout(() => {
          chatContainer.value.scrollTop = chatContainer.value.scrollHeight;
        }, 100);
      }
    };

    // 发送消息
    const sendMessage = async () => {
      const message = userMessage.value.trim();
      if (!message || isTyping.value) {
        return;
      }

      // 清空输入框
      userMessage.value = '';

      // 添加用户消息
      store.addChatMessage({
        content: message,
        role: 'user'
      });

      scrollToBottom();

      // 添加AI正在输入的消息
      isTyping.value = true;
      const assistantMessage = store.addChatMessage({
        content: '',
        role: 'assistant',
        isStreaming: true,
        references: []
      });

      try {
        // 处理聊天流
        await processChatStream(
          message,
          // 处理token
          (text) => {
            store.updateChatMessage(assistantMessage.id, {
              content: assistantMessage.content + text
            });
            scrollToBottom();
          },
          // 处理引用
          (citation) => {
            const references = [...(assistantMessage.references || [])];
            const existingIndex = references.findIndex(ref => ref.id === citation.citation_id);
            
            if (existingIndex === -1) {
              references.push({
                id: citation.citation_id,
                text: citation.snippet || '',
                page: citation.page,
                citationId: citation.citation_id,
                rank: citation.rank,
                previewUrl: citation.previewUrl
              });
              
              store.updateChatMessage(assistantMessage.id, {
                references
              });
            }
          },
          // 处理完成
          (data) => {
            isTyping.value = false;
            store.updateChatMessage(assistantMessage.id, {
              isStreaming: false
            });
            scrollToBottom();
          },
          // 处理错误
          (error) => {
            isTyping.value = false;
            ElMessage.error(`Error: ${error}`);
            store.updateChatMessage(assistantMessage.id, {
              isStreaming: false,
              content: `I'm sorry, an error occurred: ${error}`
            });
          },
          // PDF文件ID
          activePdfFile.value ? activePdfFile.value.id : null,
          // 会话ID
          store.currentSessionId
        );
      } catch (error) {
        isTyping.value = false;
        ElMessage.error('Failed to send message');
        console.error('Chat error:', error);
        store.updateChatMessage(assistantMessage.id, {
          isStreaming: false,
          content: 'I\'m sorry, I couldn\'t process your request at the moment.'
        });
      }
    };

    // 处理键盘事件
    const handleKeyDown = (event) => {
      if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
      }
    };

    // 清空聊天
    const clearChat = async () => {
      try {
        await store.clearSession(store.currentSessionId);
        store.clearChatMessages();
        ElMessage.success('Chat cleared');
      } catch (error) {
        console.error('Clear chat error:', error);
        ElMessage.error('Failed to clear chat');
        store.clearChatMessages(); // 即使API调用失败，也清空本地聊天记录
      }
    };

    // 复制消息
    const copyMessage = (message) => {
      navigator.clipboard.writeText(message.content)
        .then(() => ElMessage.success('Message copied'))
        .catch(() => ElMessage.error('Failed to copy message'));
    };

    // 查看引用
    const viewCitation = (citation) => {
      if (activePdfFile.value) {
        // 切换到PDF面板并跳转到对应页面
        ElMessage.info(`Viewing citation from page ${citation.page}`);
        // 在实际应用中，这里应该有逻辑来切换到PDF面板并跳转到指定页面
      }
    };

    // 渲染Markdown内容
    const renderMarkdown = (content, references = []) => {
      let renderedContent = md.render(content);
      
      // 如果有引用，添加引用列表
      if (references && references.length > 0) {
        const referencesList = references.map((ref, index) => {
          return `
<div class="citation-item" data-citation-id="${ref.citationId}" data-page="${ref.page}">
  <span class="citation-number">[${index + 1}]</span>
  <span class="citation-text">${ref.text}</span>
  <button class="view-citation-btn" title="View on PDF page ${ref.page}">
    <Link size="14" />
  </button>
</div>`;
        }).join('');
        
        renderedContent += `
<div class="citations-section">
  <h4>References:</h4>
  <div class="citations-list">
    ${referencesList}
  </div>
</div>`;
      }
      
      return renderedContent;
    };

    // 生命周期钩子
    onMounted(() => {
      // 添加示例消息以展示界面功能
      if (chatMessages.value.length === 0) {
        store.addChatMessage({
          content: "Welcome to the Multimodal RAG Retrieval System!\n\nI can help you analyze and query information from your PDF documents. Here's how to get started:\n\n1. Upload a PDF document using the upload button\n2. Wait for the document to be parsed and indexed\n3. Ask me questions about the content\n4. I'll provide answers with citations to the original content\n\nTry uploading a PDF and asking me something about it!",
          role: 'assistant',
          references: []
        });
      }
      
      // 添加事件监听器处理引用点击
      const handleCitationClick = (event) => {
        const citationItem = event.target.closest('.citation-item');
        const viewBtn = event.target.closest('.view-citation-btn');
        
        if (viewBtn && citationItem) {
          event.preventDefault();
          const citationId = citationItem.dataset.citationId;
          const page = parseInt(citationItem.dataset.page);
          
          const citation = chatMessages.value.flatMap(msg => msg.references || []).find(ref => ref.citationId === citationId);
          if (citation) {
            viewCitation(citation);
          }
        }
      };
      
      if (chatContainer.value) {
        chatContainer.value.addEventListener('click', handleCitationClick);
      }
      
      // 清理函数
      return () => {
        if (chatContainer.value) {
          chatContainer.value.removeEventListener('click', handleCitationClick);
        }
      };
    });

    return {
      userMessage,
      isTyping,
      chatMessages,
      chatContainer,
      activePdfFile,
      sendMessage,
      handleKeyDown,
      clearChat,
      copyMessage,
      renderMarkdown
    };
  },
  template: `
    <div class="chat-interface">
      <!-- 聊天头部 -->
      <div class="chat-header">
        <div class="chat-title">
          <span class="chat-icon">💬</span>
          <h2>Chat Assistant</h2>
        </div>
        <div class="chat-actions">
          <ElButton 
            type="text" 
            icon="Refresh" 
            @click="clearChat"
            title="Clear chat"
            :loading="isTyping"
          />
        </div>
      </div>

      <!-- 聊天内容区域 -->
      <div ref="chatContainer" class="chat-messages">
        <!-- 欢迎提示 -->
        <div v-if="chatMessages.length === 0" class="welcome-message">
          <div class="welcome-content">
            <span class="welcome-icon">💬</span>
            <p>Upload a PDF document and start asking questions!</p>
          </div>
        </div>

        <!-- 消息列表 -->
        <div 
          v-for="message in chatMessages" 
          :key="message.id"
          :class="['message-item', 'message-' + message.role]"
        >
          <!-- 头像 -->
          <div class="message-avatar">
            <ElAvatar 
              :icon="message.role === 'user' ? 'User' : 'Robot'"
              size="small"
            />
          </div>

          <!-- 消息内容 -->
          <div class="message-content">
            <ApiImageRenderer
              :content="message.content"
              :references="message.references"
              @click="copyMessage(message)"
              class="message-text"
              title="Click to copy message"
            />
            
            <!-- 消息状态 -->
            <div v-if="message.isStreaming" class="message-status">
              <div class="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          </div>
        </div>

        <!-- 错误提示 -->
        <div 
          v-if="activePdfFile && !activePdfFile.isIndexed" 
          class="alert-message"
        >
          <Warning class="alert-icon" />
          <p>Your document is being processed. Please wait before asking questions.</p>
        </div>
      </div>

      <!-- 消息输入区域 -->
      <div class="chat-input-area">
        <ElInput
          v-model="userMessage"
          type="textarea"
          placeholder="Ask a question about your document..."
          :rows="3"
          :disabled="isTyping"
          @keydown="handleKeyDown"
          resize="none"
          class="message-input"
        />
        
        <div class="input-actions">
          <ElButton
            type="primary"
            icon="Paperclip"
            @click="sendMessage"
            :loading="isTyping"
            :disabled="!userMessage.trim() || isTyping"
            round
            class="send-button"
          >
            Send
          </ElButton>
        </div>
      </div>
    </div>
  `
};