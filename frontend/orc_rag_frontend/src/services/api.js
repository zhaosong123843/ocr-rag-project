// API服务层 - 处理所有后端API调用
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001/api/v1';

// 创建axios实例
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json'
  }
});

// 健康检查
export async function checkHealth() {
  try {
    const response = await apiClient.get('/health');
    return response.data;
  } catch (error) {
    console.error('Health check failed:', error);
    throw new Error('API unavailable');
  }
}

// PDF上传
export async function uploadPdf(file, replace = true) {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('replace', replace.toString());

  const response = await apiClient.post('/pdf/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  });

  return response.data;
}

// 开始PDF解析
export async function startParse(fileId) {
  const response = await apiClient.post('/pdf/parse', {
    fileId
  });

  return response.data;
}

// 查询解析状态
export async function getParseStatus(fileId) {
  const response = await apiClient.get('/pdf/status', {
    params: {
      fileId
    }
  });
  return response.data;
}

// 获取PDF页面图片
export function getPdfPageUrl(fileId, page, type = 'original') {
  return `${API_BASE_URL}/pdf/page?fileId=${encodeURIComponent(fileId)}&page=${page}&type=${type}`;
}

// 获取Citation详情
export async function getCitationChunk(citationId) {
  const response = await apiClient.get(`/pdf/chunk?citationId=${encodeURIComponent(citationId)}`);
  return response.data;
}

// 构建向量索引
export async function buildIndex(fileId) {
  const response = await apiClient.post('/index/build', {
    fileId
  });

  return response.data;
}

// 搜索索引
export async function searchIndex(fileId, query, k = 5) {
  const response = await apiClient.post('/index/search', {
    fileId,
    query,
    k
  });

  return response.data;
}

// 自定义SSE处理函数
export async function processChatStream(
  message,
  onToken,
  onCitation,
  onDone,
  onError,
  fileID = null,
  sessionId = 'default'
) {
  try {
    const requestBody = {
      message,
      sessionId
    };
    
    if (fileID) {
      requestBody.fileID = fileID;
    }
    
    const response = await fetch(`${API_BASE_URL}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'text/event-stream',
      },
      body: JSON.stringify(requestBody),
    });

    if (!response.ok) {
      throw new Error(`Chat request failed: ${response.statusText}`);
    }

    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error('No response body');
    }

    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      
      // 处理SSE事件
      const events = buffer.split('\n\n');
      buffer = events.pop() || ''; // 保留最后一个不完整的事件

      for (const event of events) {
        if (!event.trim()) continue;

        const lines = event.split('\n');
        let eventType = '';
        let eventData = '';

        for (const line of lines) {
          if (line.startsWith('event: ')) {
            eventType = line.substring(7);
          } else if (line.startsWith('data: ')) {
            eventData = line.substring(6);
          }
        }

        if (eventType && eventData) {
          try {
            // Enhanced JSON parsing with more robust error handling
            let data;
            try {
              // 首先检查是否是有效的JSON字符串
              const trimmedData = eventData.trim();
              if (trimmedData.startsWith('{') && trimmedData.endsWith('}')) {
                data = JSON.parse(trimmedData);
              } else if (trimmedData.startsWith('[') && trimmedData.endsWith(']')) {
                data = JSON.parse(trimmedData);
              } else {
                // 如果不是JSON对象，可能是纯文本
                throw new Error('Not a JSON object');
              }
            } catch (parseError) {
              console.error('Failed to parse SSE data:', parseError);
              console.log('Event type:', eventType);
              console.log('Raw event data:', eventData);
              console.log('Event data length:', eventData.length);
              console.log('First few characters:', eventData.substring(0, 50));
              
              // Special handling for different event types
              if (eventType === 'token') {
                // For token events, treat as plain text
                onToken(eventData || '[Unparseable content]');
                continue;
              } else if (eventType === 'done') {
                // For done events, call with minimal data
                onDone({ success: true });
                return;
              } else if (eventType === 'citation') {
                // For citation events, try to create minimal structure
                onCitation({ text: eventData });
                continue;
              } else if (eventType === 'error') {
                // For error events, pass the raw message
                onError(eventData || 'Unknown error');
                return;
              }
              continue;
            }
            
            switch (eventType) {
              case 'citation':
                onCitation(data || {});
                break;
              case 'token':
                // Ensure we have text property or use the whole data
                onToken(data.text || (typeof data === 'string' ? data : JSON.stringify(data)));
                break;
              case 'done':
                onDone(data || {});
                return;
              case 'error':
                onError(data.message || 'Unknown error');
                return;
            }
          } catch (e) {
            console.error('Error processing SSE event:', e);
          }
        }
      }
    }
  } catch (error) {
    // 如果API不可用，提供一个模拟响应
    if (error instanceof TypeError && error.message.includes('Failed to fetch')) {
      // 模拟响应以展示界面功能
      const mockResponse = `I understand you're asking about: "${message}".

Since the backend API is not currently available, I'm showing you a demonstration of the interface. 

## Key Features Demonstrated:
- **Markdown rendering**: This response shows how text formatting works
- **Code blocks**: Here's an example:

\`\`\`javascript
// Example code with syntax highlighting
function processDocument(content) {
  return content.split('\\n').map(line => ({
    text: line,
    analysis: performAnalysis(line)
  }));
}
\`\`\`

- **Reference citations**: This would normally include citations like [1] and [2] when connected to a real backend
- **Streaming responses**: Text appears progressively as it would from the AI

To see the full functionality, please start the backend server at \`localhost:8001\` and upload a PDF document.`;

      // 模拟流式响应
      const words = mockResponse.split(' ');
      let currentIndex = 0;
      
      const streamInterval = setInterval(() => {
        if (currentIndex < words.length) {
          onToken(words[currentIndex] + ' ');
          currentIndex++;
        } else {
          clearInterval(streamInterval);
          onDone({ used_retrieval: false });
        }
      }, 50);
      
      return;
    }
    
    onError(error instanceof Error ? error.message : 'Unknown error');
  }
}

// 清空聊天会话
export async function clearSession(sessionId = 'default') {
  const response = await apiClient.post('/chat/clear', {
    sessionId
  });

  return response.data;
}

// 获取所有PDF文件名
export async function getPdfFiles() {
  try {
    const response = await apiClient.get('/pdf/file_names');
    // 后端返回格式：{"files": [{"file_name": "原始文件名", "random_name": "随机文件名"}, ...]}
    return response.data;
  } catch (error) {
    console.error('获取PDF文件列表失败:', error);
    // 如果API不可用，返回空数组
    return { files: [] };
  }
}

// 根据文件id获取文件页面
export async function getPdfPageByFileName(fileId, page, type = 'original') {
  try {
    const response = await fetch(`${API_BASE_URL}/pdf/file-by-name?page=${page}&type=${type}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ file_id: fileId })
    });
    
    if (!response.ok) {
      throw new Error(`获取文件页面失败: ${response.statusText}`);
    }
    
    // 处理图片blob数据
    const blob = await response.blob();
    return URL.createObjectURL(blob);
  } catch (error) {
    console.error('根据文件名获取文件页面失败:', error);
    throw error;
  }
}

// 获取PDF文件总页数
export async function getPdfPages(fileId) {
  try {
    const response = await apiClient.get(`/pdf/pages?fileId=${encodeURIComponent(fileId)}`);
    return response.data;
  } catch (error) {
    console.error('获取PDF页数失败:', error);
    throw error;
  }
}