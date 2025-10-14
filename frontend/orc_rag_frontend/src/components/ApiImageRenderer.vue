<template>
  <div class="api-image-renderer">
    <img 
      v-if="isApiImage" 
      :src="imageSrc" 
      :alt="altText" 
      class="api-image"
      @error="handleImageError"
      @load="handleImageLoad"
    />
    <div v-else v-html="renderedContent" class="markdown-content"></div>
  </div>
</template>

<script>
import { ref, computed, onMounted } from 'vue';
import MarkdownIt from 'markdown-it';

const md = new MarkdownIt({
  html: true,
  linkify: true,
  typographer: true,
  breaks: true
});

export default {
  name: 'ApiImageRenderer',
  props: {
    content: {
      type: String,
      required: true
    },
    references: {
      type: Array,
      default: () => []
    }
  },
  setup(props) {
    const imageSrc = ref('');
    const altText = ref('');
    const imageError = ref(false);
    const imageLoading = ref(false);

    // 检查是否为API图片
    const isApiImage = computed(() => {
      // 处理完整的Markdown图片格式：![alt text](/api/...)
      const apiImageMatch = props.content.match(/!\[([^\]]*)\]\((\/api\/[^\)]+)\)/);
      if (apiImageMatch) {
        imageSrc.value = apiImageMatch[2]; // 提取URL部分
        altText.value = apiImageMatch[1] || 'API Image';
        return true;
      }
      
      // 处理纯URL格式（没有Markdown包装）
      const pureUrlMatch = props.content.match(/^\/api\/.*$/);
      if (pureUrlMatch) {
        imageSrc.value = props.content;
        altText.value = 'API Image';
        return true;
      }
      
      // 处理可能包含空格或其他字符的URL
      const urlOnlyMatch = props.content.match(/\/api\/[^\s\)\]]+/);
      if (urlOnlyMatch) {
        imageSrc.value = urlOnlyMatch[0];
        altText.value = 'API Image';
        return true;
      }
      
      return false;
    });

    // 渲染普通Markdown内容
    const renderedContent = computed(() => {
      if (isApiImage.value) return '';
      
      let content = md.render(props.content);
      
      // 添加引用列表
      if (props.references && props.references.length > 0) {
        const referencesList = props.references.map((ref, index) => {
          return `
<div class="citation-item" data-citation-id="${ref.citationId}" data-page="${ref.page}">
  <span class="citation-number">[${index + 1}]</span>
  <span class="citation-text">${ref.text}</span>
  <button class="view-citation-btn" title="View on PDF page ${ref.page}">
    <Link size="14" />
  </button>
</div>`;
        }).join('');
        
        content += `
<div class="citations-section">
  <h4>References:</h4>
  <div class="citations-list">
    ${referencesList}
  </div>
</div>`;
      }
      
      return content;
    });

    const handleImageError = () => {
      imageError.value = true;
      imageLoading.value = false;
      console.error('Failed to load API image:', imageSrc.value);
    };

    const handleImageLoad = () => {
      imageLoading.value = false;
    };

    onMounted(() => {
      if (isApiImage.value) {
        imageLoading.value = true;
      }
    });

    return {
      imageSrc,
      altText,
      isApiImage,
      renderedContent,
      imageError,
      imageLoading,
      handleImageError,
      handleImageLoad
    };
  }
};
</script>

<style scoped>
.api-image-renderer {
  display: contents;
}

.api-image {
  max-width: 100%;
  height: auto;
  border-radius: 8px;
  margin: 8px 0;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.markdown-content {
  display: contents;
}

.api-image.loading {
  opacity: 0.5;
}
</style>