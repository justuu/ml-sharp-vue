<template>
  <div class="upload-container">
    <div class="upload-card card">
      <h1>🎨 ML-Sharp 3D 生成器</h1>
      <p class="subtitle">上传图片,生成 3D Gaussian Splat 模型</p>

      <div 
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

      <button 
        class="btn btn-generate"
        :disabled="!selectedFile || isProcessing"
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

    const formatFileSize = (bytes) => {
      if (bytes < 1024) return bytes + ' B'
      if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
      return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
    }

    const handleGenerate = async () => {
      if (!selectedFile.value) return

      isProcessing.value = true
      error.value = null

      try {
        const result = await api.uploadImage(selectedFile.value)
        emit('ply-generated', {
          plyFilename: result.ply_filename,
          taskId: result.task_id,
          imageWidth: imageWidth.value,
          imageHeight: imageHeight.value
        })
      } catch (err) {
        error.value = err.response?.data?.detail || '生成失败,请重试'
        console.error('Upload error:', err)
      } finally {
        isProcessing.value = false
      }
    }

    return {
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
</style>
