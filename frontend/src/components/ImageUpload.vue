<template>
  <div class="upload-container">
    <div class="upload-card card">
      <h1>🎨 ML-Sharp 3D 生成器</h1>
      <p class="subtitle">上传图片或输入 OSS 链接,生成 3D Gaussian Splat 模型</p>

      <!-- 选项卡切换 -->
      <div class="tabs">
        <button 
          class="tab-btn" 
          :class="{ active: inputMode === 'upload' }"
          @click="inputMode = 'upload'"
        >本地上传</button>
        <button 
          class="tab-btn" 
          :class="{ active: inputMode === 'url' }"
          @click="inputMode = 'url'"
        >OSS 链接</button>
      </div>

      <!-- 本地上传模式 -->
      <div v-show="inputMode === 'upload'"
        class="drop-zone"
        :class="{ 'drag-over': isDragging }"
        @drop.prevent="handleDrop"
        @dragover.prevent="isDragging = true"
        @dragleave.prevent="isDragging = false"
      >
        <input
          ref="fileInput"
          type="file"
          accept="image/jpeg,image/jpg,image/png,image/webp"
          @change="handleFileSelect"
          style="display: none"
        />

        <div v-if="!selectedFile" class="drop-zone-content">
          <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
            <polyline points="17 8 12 3 7 8"></polyline>
            <line x1="12" y1="3" x2="12" y2="15"></line>
          </svg>
          <p>拖拽图片到这里或点击选择</p>
          <button class="btn" @click="$refs.fileInput.click()">选择图片</button>
        </div>

        <div v-else class="preview-container">
          <img :src="previewUrl" alt="Preview" class="preview-image" />
          <div class="file-info">
            <p class="file-name">{{ selectedFile.name }}</p>
            <p class="file-size">{{ formatFileSize(selectedFile.size) }}</p>
          </div>
          <button class="btn btn-remove" @click="removeFile">移除</button>
        </div>
      </div>

      <!-- OSS链接模式 -->
      <div v-show="inputMode === 'url'" class="url-input-zone">
        <div class="input-wrapper">
          <input 
            v-model="ossUrl" 
            type="text" 
            placeholder="请输入阿里云 OSS 图片链接..."
            class="url-input"
            @input="handleUrlInput"
          />
        </div>
        
        <div v-if="ossPreviewUrl" class="preview-container mt-2">
          <img :src="ossPreviewUrl" alt="URL Preview" class="preview-image" @error="handleUrlError" />
          <div class="file-info">
            <p class="file-name">来自 OSS 的图片</p>
          </div>
          <button class="btn btn-remove" @click="clearUrl">清除</button>
        </div>
      </div>

      <button 
        class="btn btn-generate"
        :disabled="(!selectedFile && !validOssUrl) || isProcessing"
        @click="handleGenerate"
      >
        <span v-if="isProcessing" class="loading"></span>
        <span v-else>生成 3D 模型</span>
      </button>

      <button 
        class="btn btn-test"
        @click="$refs.plyInput.click()"
        style="margin-top: 1rem; background: #6c757d;"
      >
        📂 测试本地 PLY 文件
      </button>
      <input
        ref="plyInput"
        type="file"
        accept=".ply"
        @change="handlePlySelect"
        style="display: none"
      />

      <div v-if="error" class="error-message">
        {{ error }}
      </div>
    </div>
  </div>
</template>

<script>
import { ref } from 'vue'
import { api } from '../services/api'

export default {
  name: 'ImageUpload',
  emits: ['ply-generated', 'ply-selected'],
  setup(props, { emit }) {
    const inputMode = ref('upload') // 'upload' or 'url'
    const ossUrl = ref('')
    const ossPreviewUrl = ref('')
    const validOssUrl = ref(false)

    const selectedFile = ref(null)
    const previewUrl = ref(null)
    const imageWidth = ref(null)
    const imageHeight = ref(null)
    const isDragging = ref(false)
    const isProcessing = ref(false)
    const error = ref(null)
    const fileInput = ref(null)
    const plyInput = ref(null)

    const handleFileSelect = (event) => {
      const file = event.target.files[0]
      if (file) {
        setFile(file)
      }
    }

    const handlePlySelect = (event) => {
      const file = event.target.files[0]
      if (file) {
        const url = URL.createObjectURL(file)
        emit('ply-selected', {
          url: url,
          filename: file.name
        })
      }
    }

    const handleDrop = (event) => {
      isDragging.value = false
      const file = event.dataTransfer.files[0]
      if (file && file.type.startsWith('image/')) {
        setFile(file)
      }
    }

    const setFile = (file) => {
      selectedFile.value = file
      previewUrl.value = URL.createObjectURL(file)
      imageWidth.value = null
      imageHeight.value = null
      const img = new Image()
      img.onload = () => {
        imageWidth.value = img.naturalWidth
        imageHeight.value = img.naturalHeight
      }
      img.src = previewUrl.value
      error.value = null
    }

    const removeFile = () => {
      if (previewUrl.value) {
        URL.revokeObjectURL(previewUrl.value)
      }
      selectedFile.value = null
      previewUrl.value = null
      imageWidth.value = null
      imageHeight.value = null
      error.value = null
    }

    const handleUrlInput = () => {
      validOssUrl.value = false
      ossPreviewUrl.value = ''
      error.value = null
      
      const url = ossUrl.value.trim()
      if (!url) return
      
      // Simple preview setting (assumes public read)
      ossPreviewUrl.value = url
      // We will assume it's valid if it starts to load or if text is entered
      validOssUrl.value = true
    }

    const clearUrl = () => {
      ossUrl.value = ''
      ossPreviewUrl.value = ''
      validOssUrl.value = false
      imageWidth.value = null
      imageHeight.value = null
      error.value = null
    }

    const handleUrlError = () => {
      // If image fails to load via URL, still allow submission as backend downloads it, 
      // but preview will be broken. 
      console.warn('OSS preview failed, it might be private. Will still attempt backend generation.')
    }

    const formatFileSize = (bytes) => {
      if (bytes < 1024) return bytes + ' B'
      if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
      return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
    }

    const handleGenerate = async () => {
      if (inputMode.value === 'upload' && !selectedFile.value) return
      if (inputMode.value === 'url' && !validOssUrl.value) return

      isProcessing.value = true
      error.value = null

      try {
        let result
        if (inputMode.value === 'upload') {
          result = await api.uploadImage(selectedFile.value)
        } else {
          result = await api.generateFromOssUrl(ossUrl.value.trim())
        }
        
        emit('ply-generated', {
          plyFilename: result.ply_filename,
          taskId: result.task_id,
          imageWidth: result.image_width || imageWidth.value || null,
          imageHeight: result.image_height || imageHeight.value || null
        })
      } catch (err) {
        error.value = err.response?.data?.detail || '生成失败,请重试'
        console.error('Upload error:', err)
      } finally {
        isProcessing.value = false
      }
    }

    return {
      inputMode,
      ossUrl,
      ossPreviewUrl,
      validOssUrl,
      selectedFile,
      previewUrl,
      isDragging,
      isProcessing,
      error,
      fileInput,
      plyInput,
      handleFileSelect,
      handlePlySelect,
      handleDrop,
      removeFile,
      clearUrl,
      handleUrlInput,
      handleUrlError,
      formatFileSize,
      handleGenerate
    }
  }
}
</script>

<style scoped>
.upload-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  padding: 2rem;
}

.upload-card {
  max-width: 600px;
  width: 100%;
}

h1 {
  font-size: 2.5rem;
  margin-bottom: 0.5rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.subtitle {
  color: #666;
  margin-bottom: 2rem;
  font-size: 1.1rem;
}

.drop-zone {
  border: 3px dashed #ddd;
  border-radius: 12px;
  padding: 3rem 2rem;
  text-align: center;
  transition: all 0.3s ease;
  margin-bottom: 1.5rem;
}

.drop-zone.drag-over {
  border-color: #667eea;
  background: rgba(102, 126, 234, 0.05);
}

.drop-zone-content svg {
  color: #667eea;
  margin-bottom: 1rem;
}

.drop-zone-content p {
  color: #666;
  margin-bottom: 1rem;
  font-size: 1.1rem;
}

.preview-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
}

.preview-image {
  max-width: 100%;
  max-height: 300px;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.file-info {
  text-align: center;
}

.file-name {
  font-weight: 600;
  color: #333;
  margin-bottom: 0.25rem;
}

.file-size {
  color: #999;
  font-size: 0.9rem;
}

.btn-generate {
  width: 100%;
  font-size: 1.1rem;
  padding: 1rem;
}

.btn-remove {
  background: #e74c3c;
}

.btn-remove:hover {
  box-shadow: 0 8px 20px rgba(231, 76, 60, 0.4);
}

.error-message {
  margin-top: 1rem;
  padding: 1rem;
  background: #fee;
  border: 1px solid #fcc;
  border-radius: 8px;
  color: #c33;
  text-align: center;
}

.mt-2 {
  margin-top: 1rem;
}

/* Tabs */
.tabs {
  display: flex;
  justify-content: center;
  margin-bottom: 1.5rem;
  background-color: #f1f3f5;
  border-radius: 8px;
  padding: 0.3rem;
}

.tab-btn {
  flex: 1;
  border: none;
  background: transparent;
  padding: 0.8rem 1rem;
  font-size: 1rem;
  font-weight: 600;
  color: #6c757d;
  cursor: pointer;
  border-radius: 6px;
  transition: all 0.2s ease;
}

.tab-btn.active {
  background: #fff;
  color: #667eea;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}

/* URL Input */
.url-input-zone {
  border: 1px solid #ddd;
  border-radius: 12px;
  padding: 2rem;
  margin-bottom: 1.5rem;
  display: flex;
  flex-direction: column;
}

.input-wrapper {
  width: 100%;
}

.url-input {
  width: 100%;
  padding: 1rem;
  font-size: 1rem;
  border: 2px solid #e9ecef;
  border-radius: 8px;
  transition: border-color 0.2s;
  box-sizing: border-box;
}

.url-input:focus {
  outline: none;
  border-color: #667eea;
}
</style>
