<template>
  <div id="app">
    <ImageUpload 
      v-if="!currentPlyFile && !currentPlyUrl"
      @ply-generated="handlePlyGenerated"
      @ply-selected="handlePlySelected"
    />
    <PlyViewer 
      v-else
      :ply-filename="currentPlyFile"
      :ply-url="currentPlyUrl"
      :original-width="originalWidth"
      :original-height="originalHeight"
      @back="handleBack"
    />
  </div>
</template>

<script>
import { ref } from 'vue'
import ImageUpload from './components/ImageUpload.vue'
import PlyViewer from './components/PlyViewer.vue'

export default {
  name: 'App',
  components: {
    ImageUpload,
    PlyViewer
  },
  setup() {
    const currentPlyFile = ref(null)
    const currentPlyUrl = ref(null)
    const originalWidth = ref(null)
    const originalHeight = ref(null)

    const handlePlyGenerated = (data) => {
      currentPlyFile.value = data.plyFilename
      currentPlyUrl.value = null
      originalWidth.value = data.imageWidth || null
      originalHeight.value = data.imageHeight || null
    }

    const handlePlySelected = (data) => {
      currentPlyUrl.value = data.url
      currentPlyFile.value = null
    }

    const handleBack = () => {
      currentPlyFile.value = null
      currentPlyUrl.value = null
      originalWidth.value = null
      originalHeight.value = null
    }

    return {
      currentPlyFile,
      currentPlyUrl,
      handlePlyGenerated,
      handlePlySelected,
      handleBack,
      originalWidth,
      originalHeight
    }
  }
}
</script>
