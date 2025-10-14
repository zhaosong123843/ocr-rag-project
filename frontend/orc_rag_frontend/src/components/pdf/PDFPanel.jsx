// PDF面板组件
import { ref, computed, watch } from 'vue';
import { useAppStore } from '@/store';
import { uploadPdf, startParse, getParseStatus, getPdfPageUrl, buildIndex as apiBuildIndex } from '@/services/api';
import { Upload, ArrowLeft, ArrowRight, ZoomIn, ZoomOut, SuccessFilled, Warning, Loading } from '@element-plus/icons-vue';
import { ElButton, ElUpload, ElProgress, ElMessage } from 'element-plus';

// 上传前的检查
export const beforeUpload = (file) => {
  const isPDF = file.type === 'application/pdf';
  if (!isPDF) {
    ElMessage.error('Only PDF files are allowed!');
    return false;
  }
  const isLt10M = file.size / 1024 / 1024 < 10;
  if (!isLt10M) {
    ElMessage.error('File must be less than 10MB!');
    return false;
  }
  return true;
};

export default {
  name: 'PDFPanel',
  setup() {
    const store = useAppStore();
    const uploadRef = ref(null);
    const isProcessing = ref(false);
    const processingProgress = ref(0);
    const intervalId = ref(null);
    const pdfContainer = ref(null);

    // 计算属性
    const activePdfFile = computed(() => store.getActivePdfFile);
    const pdfPage = computed(() => store.getPdfPage);
    const pdfZoom = computed(() => store.getPdfZoom);

    // 监听PDF文件变化
    watch(activePdfFile, (newFile) => {
      if (newFile && !newFile.isParsed) {
        // 开始解析PDF
        startPdfParsing(newFile.id);
      }
    });

    // 开始PDF解析
    const startPdfParsing = async (fileId) => {
      if (isProcessing.value) return;

      try {
        isProcessing.value = true;
        processingProgress.value = 0;

        // 开始解析任务
        await startParse(fileId);

        // 轮询解析状态
        intervalId.value = setInterval(async () => {
          try {
            const status = await getParseStatus(fileId);
            processingProgress.value = status.progress;
            
            // 更新store中的状态
            store.updatePdfParseProgress(status.progress);

            if (status.status === 'ready') {
              // 解析完成，构建索引
              await buildIndex(fileId);
              clearInterval(intervalId.value);
              intervalId.value = null;
              isProcessing.value = false;
              ElMessage.success('Document processed successfully!');
            } else if (status.status === 'error') {
              clearInterval(intervalId.value);
              intervalId.value = null;
              isProcessing.value = false;
              store.setPdfParseError(status.errorMsg || 'Failed to process document');
              ElMessage.error(`Error: ${status.errorMsg || 'Failed to process document'}`);
            }
          } catch (error) {
            console.error('Error checking parse status:', error);
          }
        }, 2000);
      } catch (error) {
        isProcessing.value = false;
        console.error('Error starting parse:', error);
        ElMessage.error('Failed to start processing document');
      }
    };

    // 构建索引
    const buildIndex = async (fileId) => {
      try {
        ElMessage.info('Building search index...');
        await store.setLoading(true);
        const result = await apiBuildIndex(fileId);
        if (result.ok) {
          store.setPdfIndexed(true);
          ElMessage.success(`Index built with ${result.chunks} chunks`);
        } else {
          ElMessage.error('Failed to build search index');
        }
      } catch (error) {
        console.error('Error building index:', error);
        ElMessage.error('Failed to build search index');
      } finally {
        store.setLoading(false);
      }
    };

    // 处理文件上传成功
    const handleUploadSuccess = async (response) => {
      if (response && response.fileId) {
        // 设置活跃的PDF文件
        store.setActivePdfFile({
          id: response.fileId,
          name: response.name,
          pages: response.pages,
          isParsing: true,
          parseProgress: 0,
          isParsed: false,
          isIndexed: false
        });
        
        ElMessage.success(`File "${response.name}" uploaded successfully`);
      } else {
        ElMessage.error('Failed to upload file: Invalid response');
      }
    };

    // 处理文件上传错误
    const handleUploadError = (error) => {
      console.error('Upload error:', error);
      ElMessage.error('Failed to upload file');
    };

    // 删除当前PDF文件
    const removePdfFile = () => {
      if (intervalId.value) {
        clearInterval(intervalId.value);
        intervalId.value = null;
      }
      isProcessing.value = false;
      processingProgress.value = 0;
      store.setActivePdfFile(null);
      ElMessage.success('File removed');
    };

    // 切换到上一页
    const prevPage = () => {
      store.prevPdfPage();
    };

    // 切换到下一页
    const nextPage = () => {
      store.nextPdfPage();
    };

    // 放大
    const zoomIn = () => {
      store.setPdfZoom(pdfZoom.value + 0.1);
    };

    // 缩小
    const zoomOut = () => {
      store.setPdfZoom(pdfZoom.value - 0.1);
    };

    // 重置缩放
    const resetZoom = () => {
      store.setPdfZoom(1.0);
    };

    // 获取PDF页面URL
    const getPageUrl = (page, type = 'original') => {
      if (!activePdfFile.value) return '';
      return getPdfPageUrl(activePdfFile.value.id, page, type);
    };

    // 渲染文件状态
    const renderFileStatus = () => {
      if (!activePdfFile.value) return null;

      const { isParsing, parseProgress, isParsed, isIndexed, error } = activePdfFile.value;

      if (error) {
        return (
          <div class="file-status error">
            <Warning class="status-icon" />
            <span>Error: {error}</span>
          </div>
        );
      }

      if (isParsing) {
        return (
          <div class="file-status processing">
            <Loading class="status-icon" />
            <span>Processing document ({parseProgress}%)</span>
            <ElProgress
                percentage={parseProgress}
                status={parseProgress === 100 ? 'success' : 'normal'}
                class="progress-bar"
            />
          </div>
        );
      }

      if (isParsed && isIndexed) {
        return (
          <div class="file-status ready">
            <SuccessFilled class="status-icon" />
            <span>Ready for querying</span>
          </div>
        );
      }

      if (isParsed && !isIndexed) {
        return (
          <div class="file-status warning">
            <Warning class="status-icon" />
            <span>Document parsed but not indexed</span>
          </div>
        );
      }

      return null;
    };

    // 组件卸载时清理
    const cleanup = () => {
      if (intervalId.value) {
        clearInterval(intervalId.value);
        intervalId.value = null;
      }
    };

    // 组件卸载时执行清理
    import.meta.hot?.on('vite:beforeUpdate', cleanup);

    return {
      uploadRef,
      isProcessing,
      processingProgress,
      pdfContainer,
      activePdfFile,
      pdfPage,
      pdfZoom,
      beforeUpload,
      handleUploadSuccess,
      handleUploadError,
      removePdfFile,
      prevPage,
      nextPage,
      zoomIn,
      zoomOut,
      resetZoom,
      getPageUrl,
      renderFileStatus
    };
  },
  template: `
    <div class="pdf-panel">
      <!-- PDF头部 -->
      <div class="pdf-header">
        <div class="pdf-title">
          <span class="pdf-icon">📄</span>
          <h2>Document Viewer</h2>
        </div>
        
        <!-- 上传按钮 -->
        <div v-if="!activePdfFile" class="upload-area">
          <ElUpload
            ref="uploadRef"
            :before-upload="beforeUpload"
            :on-success="handleUploadSuccess"
            :on-error="handleUploadError"
            :show-file-list="false"
            class="upload-btn"
          >
            <ElButton type="primary" icon="Upload" class="upload-button">
              Upload PDF
            </ElButton>
          </ElUpload>
          
          <p class="upload-hint">Drag and drop PDF files or click to upload</p>
        </div>
        
        <!-- 文件信息 -->
        <div v-else class="file-info">
          <span class="file-name">{{ activePdfFile.name }}</span>
          <ElButton 
            type="text" 
            icon="Delete" 
            @click="removePdfFile"
            title="Remove file"
            class="remove-button"
          />
        </div>
      </div>

      <!-- 文件状态 -->
      <div v-if="activePdfFile" class="file-status-container">
        {{ renderFileStatus() }}
      </div>

      <!-- PDF预览区域 -->
      <div class="pdf-preview" ref="pdfContainer">
        <!-- 占位符 -->
        <div v-if="!activePdfFile" class="preview-placeholder">
          <span class="placeholder-icon">📄</span>
          <p>Upload a PDF document to view it here</p>
        </div>
        
        <!-- PDF内容 -->
        <div v-else-if="activePdfFile.isParsed" class="pdf-content">
          <div
              class="pdf-page"
              style={{ transform: "scale(" + pdfZoom + ")" }}
            >
            <img
                :src="getPageUrl(pdfPage, 'original')"
                :alt="'Page ' + pdfPage + ' of ' + activePdfFile.name"
                class="pdf-image"
            />
          </div>
        </div>
        
        <!-- 加载中 -->
        <div v-else class="loading-preview">
          <Loading class="loading-icon" />
          <p>Processing document, please wait...</p>
        </div>
      </div>

      <!-- PDF控制栏 -->
      <div v-if="activePdfFile && activePdfFile.isParsed" class="pdf-controls">
        <!-- 页面控制 -->
        <div class="page-controls">
          <ElButton 
            type="text" 
            icon="ArrowLeft" 
            @click="prevPage"
            :disabled="pdfPage <= 1"
          />
          <span class="page-info">
            Page {{ pdfPage }} of {{ activePdfFile.pages }}
          </span>
          <ElButton 
            type="text" 
            icon="ArrowRight" 
            @click="nextPage"
            :disabled="pdfPage >= activePdfFile.pages"
          />
        </div>
        
        <!-- 缩放控制 -->
        <div class="zoom-controls">
          <ElButton 
            type="text" 
            icon="ZoomOut" 
            @click="zoomOut"
            :disabled="pdfZoom <= 0.5"
          />
          <span class="zoom-info">{{ Math.round(pdfZoom * 100) }}%</span>
          <ElButton 
            type="text" 
            icon="ZoomIn" 
            @click="zoomIn"
            :disabled="pdfZoom >= 2.0"
          />
          <ElButton 
            type="text" 
            @click="resetZoom"
          >
            100%
          </ElButton>
        </div>
      </div>
    </div>
  `
};