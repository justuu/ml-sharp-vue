<template>
  <div class="viewer-container">
    <div class="viewer-card card">
      <div class="viewer-header">
        <h2>🎯 3D 可视化 (gsplat)</h2>
        <div class="header-controls">
          <div class="button-group">
            <button class="btn btn-small" @click="resetCamera">重置视角</button>
            <button class="btn btn-small btn-capture" @click="captureScreenshot">
              📸 截图
            </button>
            <button class="btn btn-small btn-back" @click="$emit('back')">
              返回
            </button>
          </div>
        </div>
      </div>

      <div ref="canvasWrapper" class="canvas-container">
        <div class="canvas-frame" :style="canvasStyle">
          <canvas ref="canvas"></canvas>
        </div>
      </div>

      <div class="info-panel">
        <p>🖱️ 左键旋转 | 右键平移 | 滚轮缩放 | 拖动滑块调整点大小</p>
      </div>

      <div v-if="loading" class="loading-overlay">
        <div class="loading-spinner"></div>
        <p>加载 3D Gaussian Splat 模型中...</p>
      </div>

      <div v-if="error" class="error-message">
        {{ error }}
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, onUnmounted, watch, computed } from 'vue'
import * as SPLAT from 'gsplat'
import { api } from '../services/api'

export default {
  name: 'PlyViewer',
  props: {
    plyFilename: {
      type: String,
      default: null
    },
    plyUrl: {
      type: String,
      default: null
    },
    originalWidth: {
      type: Number,
      default: null
    },
    originalHeight: {
      type: Number,
      default: null
    }
  },
  emits: ['back'],
  setup(props) {
    const canvas = ref(null)
    const canvasWrapper = ref(null)
    const loading = ref(true)
    const error = ref(null)
    const frameWidth = ref(0)
    const frameHeight = ref(0)
    // gsplat components
    let scene = null
    let camera = null
    let renderer = null
    let controls = null
    let animationId = null
    let currentSplat = null
    let handleResize = null

    const initViewer = () => {
      try {
        console.log('Initializing gsplat viewer...')
        scene = new SPLAT.Scene()
        camera = new SPLAT.Camera()
        renderer = new SPLAT.WebGLRenderer(canvas.value)
        controls = new SPLAT.OrbitControls(camera, canvas.value)
        
        // Setup simple orbit controls settings
        controls.minZoom = 0.1
        controls.maxZoom = 100
        
        // Default camera position - typical for looking at origin
        camera.position = new SPLAT.Vector3(0, 0, 5)

        handleResize = () => {
          if (canvasWrapper.value) {
            const availableWidth = canvasWrapper.value.clientWidth
            const availableHeight = canvasWrapper.value.clientHeight
            if (props.originalWidth && props.originalHeight) {
              const ratio = props.originalWidth / props.originalHeight
              let width = availableWidth
              let height = width / ratio
              if (height > availableHeight) {
                height = availableHeight
                width = height * ratio
              }
              frameWidth.value = Math.max(1, Math.floor(width))
              frameHeight.value = Math.max(1, Math.floor(height))
            } else {
              frameWidth.value = Math.max(1, Math.floor(availableWidth))
              frameHeight.value = Math.max(1, Math.floor(availableHeight))
            }
            renderer.setSize(frameWidth.value, frameHeight.value)
          }
        }
        window.addEventListener('resize', handleResize)
        handleResize() // Initial sizing

        // Render loop
        const frame = () => {
          controls.update()
          renderer.render(scene, camera)
          animationId = requestAnimationFrame(frame)
        }
        frame()

      } catch (err) {
        console.error('Init error:', err)
        error.value = 'Viewer rendering intialization failed: ' + err.message
        loading.value = false
      }
    }

    const loadPLY = async () => {
      loading.value = true
      error.value = null
      currentSplat = null

      try {
        const url = props.plyUrl || (props.plyFilename ? api.getPlyUrl(props.plyFilename) : null)
        if (!url) throw new Error('No PLY URL provided')

        console.log('Loading PLY from:', url)

        // Fetch the file as a buffer to sanitize the header
        const response = await fetch(url)
        if (!response.ok) throw new Error(`Failed to fetch PLY: ${response.statusText}`)
        const buffer = await response.arrayBuffer()

        // Sanitize header: Fix type names and whitespace issues
        const headerBytes = new Uint8Array(buffer)
        const decoder = new TextDecoder('utf-8')
        
        // Find header end
        let headerEnd = -1
        const searchLimit = Math.min(buffer.byteLength, 4096)
        
        for (let i = 0; i < searchLimit; i++) {
             if (headerBytes[i] === 10) { // \n
                 const chunk = headerBytes.subarray(0, i + 1)
                 const text = decoder.decode(chunk)
                 if (text.includes('end_header')) {
                     headerEnd = i + 1
                     break
                 }
             }
        }

        let finalBuffer = buffer
        
        if (headerEnd !== -1) {
             console.log('Sanitizing PLY header...')
             
             const rawHeaderBytes = new Uint8Array(buffer, 0, headerEnd)
             const rawHeaderStr = decoder.decode(rawHeaderBytes)
             
             const lines = rawHeaderStr.split(/\r?\n/)
             const sanitizedLines = []
             let inVertex = false
             let hasVertex = false
             
             for (let line of lines) {
                 const trimmed = line.trim()
                 if (!trimmed) continue
                 if (trimmed === 'end_header') continue
                 
                 if (trimmed.startsWith('element ')) {
                     if (trimmed.startsWith('element vertex')) {
                         const parts = trimmed.split(/\s+/)
                         sanitizedLines.push(parts.length >= 3 ? `element vertex ${parts[2]}` : trimmed)
                         inVertex = true
                         hasVertex = true
                     } else {
                         inVertex = false
                     }
                     continue
                 }
                 
                 if (trimmed.startsWith('property')) {
                     if (!inVertex) continue
                     const parts = trimmed.split(/\s+/)
                     if (parts.length >= 3) {
                         let type = parts[1].replace(/[^a-zA-Z0-9]/g, '')
                         if (type === 'uint') type = 'int'
                         if (type !== 'float' && type !== 'int') continue
                         sanitizedLines.push(`property ${type} ${parts.slice(2).join(' ')}`)
                     } else {
                         sanitizedLines.push(trimmed)
                     }
                     continue
                 }
                 
                 if (!hasVertex) {
                     sanitizedLines.push(trimmed)
                 }
             }
             
             sanitizedLines.push('end_header')
             
             // Reconstruct header with clean \n line endings
             const newHeaderString = sanitizedLines.join('\n') + '\n'
             
             const encoder = new TextEncoder()
             const newHeaderBytes = encoder.encode(newHeaderString)
             
             const bodyBytes = new Uint8Array(buffer, headerEnd)
             const newBuffer = new Uint8Array(newHeaderBytes.length + bodyBytes.length)
             newBuffer.set(newHeaderBytes)
             newBuffer.set(bodyBytes, newHeaderBytes.length)
             
             finalBuffer = newBuffer.buffer
             
             console.log('Sanitized header preview:', newHeaderString.substring(0, 500))
        }

        // Use LoadFromArrayBuffer
        // Note: Check if LoadFromArrayBuffer adds it to scene automatically?
        // Method signature: LoadFromArrayBuffer(arrayBuffer, scene) -> Splat
        const splat = SPLAT.PLYLoader.LoadFromArrayBuffer(finalBuffer, scene)
        currentSplat = splat
        
        console.log('Loaded splat:', splat)
        loading.value = false
        
        fitCameraToSplat()
        
      } catch (err) {
        console.error('Loading error:', err)
        error.value = '加载失败: ' + err.message
        loading.value = false
      }
    }

    const fitCameraToSplat = () => {
        if (!currentSplat || !scene) return

        console.log('Fishing camera to splat orientation...')
        
        // Correct gsplat usage:
        // 1. Vector3 properties are readonly, assign new Vector3 to object position
        // 2. OrbitControls has setCameraTarget method, no target property
        
        // Initial view: Camera at origin, looking at +Z (depth)
        camera.position = new SPLAT.Vector3(0, 0, 0)
        controls.setCameraTarget(new SPLAT.Vector3(0, 0, 2))
        controls.update()
    }

    const resetCamera = () => {
        if (controls) {
            // Match the initial "fitCameraToSplat" logic which works for ML-Sharp
            // Camera at origin (0,0,0), looking towards +Z (e.g. 0,0,2)
            camera.position = new SPLAT.Vector3(0, 0, 0)
            controls.setCameraTarget(new SPLAT.Vector3(0, 0, 2))
            controls.update()
            
            console.log('Camera reset to origin looking at +Z')
        }
    }

    const captureScreenshot = () => {
        if (!renderer || !renderer.canvas) return
        // Export at original image resolution
        const targetWidth = props.originalWidth || renderer.canvas.width
        const targetHeight = props.originalHeight || renderer.canvas.height
        const previousWidth = renderer.canvas.width
        const previousHeight = renderer.canvas.height

        // Scale camera focal lengths proportionally so the view matches the UI
        // Without this, enlarging the canvas makes the scene appear smaller
        const scaleX = targetWidth / previousWidth
        const scaleY = targetHeight / previousHeight
        const prevFx = camera.data.fx
        const prevFy = camera.data.fy
        camera.data.fx = prevFx * scaleX
        camera.data.fy = prevFy * scaleY

        renderer.setSize(targetWidth, targetHeight)
        controls.update()
        renderer.render(scene, camera)

        const sourceCanvas = renderer.canvas
        const tempCanvas = document.createElement('canvas')
        tempCanvas.width = targetWidth
        tempCanvas.height = targetHeight
        const ctx = tempCanvas.getContext('2d')
        ctx.fillStyle = '#000000'
        ctx.fillRect(0, 0, tempCanvas.width, tempCanvas.height)
        ctx.drawImage(sourceCanvas, 0, 0)
        const dataURL = tempCanvas.toDataURL('image/png')
        const link = document.createElement('a')
        link.download = `gsplat-capture-${Date.now()}.png`
        link.href = dataURL
        link.click()

        // Restore camera focal lengths and canvas size
        camera.data.fx = prevFx
        camera.data.fy = prevFy
        renderer.setSize(previousWidth, previousHeight)
        renderer.render(scene, camera)
    }

    onMounted(async () => {
      initViewer()
      await loadPLY()
    })

    onUnmounted(() => {
      cancelAnimationFrame(animationId)
      if (renderer) renderer.dispose() // if dispose exists
      // Remove resize listener
    })

    const canvasStyle = computed(() => {
      if (frameWidth.value > 0 && frameHeight.value > 0) {
        return {
          width: `${frameWidth.value}px`,
          height: `${frameHeight.value}px`
        }
      }
      return { width: '100%', height: '100%' }
    })

    watch(
      () => [props.originalWidth, props.originalHeight],
      () => {
        if (handleResize) handleResize()
      }
    )

    return {
      canvas,
      canvasWrapper,
      loading,
      error,
      resetCamera,
      captureScreenshot,
      canvasStyle
    }
  }
}
</script>

<style scoped>
.viewer-container {
  display: flex;
  justify-content: center;
  height: 100vh;
  min-height: 100vh;
  padding: 2rem;
  background-color: #0f172a;
  box-sizing: border-box;
  overflow: hidden;
}

.viewer-card {
  max-width: 1200px;
  width: 100%;
  height: 100%;
  max-height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
  background: rgba(30, 30, 46, 0.8);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 16px;
  overflow: hidden; 
}

.viewer-header {
  padding: 1rem 1.5rem;
  background: rgba(255, 255, 255, 0.05);
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 1rem;
}

.viewer-header h2 {
  font-size: 1.5rem;
  margin: 0;
  font-weight: 700;
  background: linear-gradient(135deg, #a78bfa 0%, #f472b6 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.header-controls {
  display: flex;
  align-items: center;
  gap: 1.5rem;
  flex-wrap: wrap;
}

.control-group {
    display: none; /* Hidden as requested */
}

.button-group {
    display: flex;
    gap: 0.8rem;
}

.btn-small {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 6px;
  font-weight: 500;
  cursor: pointer;
  color: white;
  background: rgba(255, 255, 255, 0.1);
  transition: all 0.2s;
}

.btn-small:hover {
  background: rgba(255, 255, 255, 0.2);
  transform: translateY(-1px);
}

.btn-capture {
  background: linear-gradient(135deg, #8b5cf6 0%, #ec4899 100%);
}

.btn-back {
    background: transparent;
    border: 1px solid rgba(255,255,255,0.2);
}

.canvas-container {
  flex: 1;
  position: relative;
  min-height: 0;
  max-height: 100%;
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.canvas-frame {
  background: #000;
}

canvas {
    width: 100%;
    height: 100%;
    display: block;
}

.info-panel {
  padding: 0.5rem;
  text-align: center;
  color: #64748b;
  font-size: 0.85rem;
  border-top: 1px solid rgba(255,255,255,0.05);
}

.loading-overlay {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  color: #e2e8f0;
  pointer-events: none;
}

.loading-spinner {
    width: 40px;
    height: 40px;
    border: 3px solid rgba(255,255,255,0.1);
    border-top-color: #a78bfa;
    border-radius: 50%;
    animation: spin 1s linear infinite;
    margin-bottom: 1rem;
}

.error-message {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    padding: 1rem 2rem;
    background: rgba(220, 38, 38, 0.2);
    border: 1px solid rgba(220, 38, 38, 0.5);
    border-radius: 8px;
    color: #fca5a5;
    text-align: center;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
