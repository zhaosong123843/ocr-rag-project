<template>
  <div class="image-loader">
    <!-- 加载状态 -->
    <div v-if="loading" class="image-loading">
      <div class="loading-spinner"></div>
      <span>Loading image...</span>
    </div>
    
    <!-- 错误状态 -->
    <div v-else-if="error" class="image-error">
      <div class="error-icon">⚠️</div>
      <span>Failed to load image</span>
      <button @click="retryLoad" class="retry-btn">Retry</button>
    </div>
    
    <!-- 成功加载 -->
    <img 
      v-else
      :src="imageUrl" 
      :alt="altText" 
      class="loaded-image"
      @load="handleImageLoad"
      @error="handleImageError"
    />
  </div>
</template>

<script>
import { ref, onMounted, watch } from 'vue';

export default {
  name: 'ImageLoader',
  props: {
    src: {
      type: String,
      required: true
    },
    alt: {
      type: String,
      default: 'Image'
    }
  },
  setup(props) {
    const imageUrl = ref('');
    const loading = ref(false);
    const error = ref(false);

    // 提取图片URL（处理Markdown格式和纯URL）
    const extractImageUrl = (content) => {
      // 处理Markdown格式：![alt text](/api/...)
      const markdownMatch = content.match(/!\[([^\]]*)\]\((\/api\/[^\)]+)\)/);
      if (markdownMatch) {
        return {
          url: markdownMatch[2],
          alt: markdownMatch[1] || 'API Image'
        };
      }
      
      // 处理纯URL
      const urlMatch = content.match(/\/api\/[^\s\)\]]+/);
      if (urlMatch) {
        return {
          url: urlMatch[0],
          alt: 'API Image'
        };
      }
      
      return null;
    };

    // 使用Fetch API加载图片
    const loadImageWithFetch = async (url) => {
      try {
        loading.value = true;
        error.value = false;
        
        const response = await fetch(url, {
          method: 'GET',
          headers: {
            'Accept': 'image/*'
          }
        });
        
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const blob = await response.blob();
        imageUrl.value = URL.createObjectURL(blob);
        
      } catch (err) {
        console.error('Failed to load image:', err);
        error.value = true;
        imageUrl.value = '';
      } finally {
        loading.value = false;
      }
    };

    // 重试加载
    const retryLoad = () => {
      const extracted = extractImageUrl(props.src);
      if (extracted) {
        loadImageWithFetch(extracted.url);
      }
    };

    // 图片加载成功
    const handleImageLoad = () => {
      loading.value = false;
      error.value = false;
    };

    // 图片加载失败
    const handleImageError = () => {
      loading.value = false;
      error.value = true;
    };

    // 监听props.src变化
    watch(() => props.src, (newSrc) => {
      const extracted = extractImageUrl(newSrc);
      if (extracted) {
        loadImageWithFetch(extracted.url);
      }
    });

    // 组件挂载时加载图片
    onMounted(() => {
      const extracted = extractImageUrl(props.src);
      if (extracted) {
        loadImageWithFetch(extracted.url);
      }
    });

    return {
      imageUrl,
      loading,
      error,
      altText: extractImageUrl(props.src)?.alt || props.alt,
      retryLoad,
      handleImageLoad,
      handleImageError
    };
  }
};
</script>

<style scoped>
.image-loader {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 200px;
  margin: 16px 0;
}

.loaded-image {
  max-width: 100%;
  max-height: 400px;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  object-fit: contain;
}

.image-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  color: #666;
}

.loading-spinner {
  width: 32px;
  height: 32px;
  border: 3px solid #e5e7eb;
  border-top: 3px solid #3b82f6;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.image-error {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  color: #dc2626;
  padding: 20px;
  border: 2px dashed #fecaca;
  border-radius: 8px;
  background-color: #fef2f2;
}

.error-icon {
  font-size: 24px;
}

.retry-btn {
  padding: 8px 16px;
  background-color: #3b82f6;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  transition: background-color 0.2s;
}

.retry-btn:hover {
  background-color: #2563eb;
}
</style>