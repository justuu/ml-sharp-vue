import axios from 'axios'

const API_BASE_URL = '/api'

export const api = {
    /**
     * Upload image and generate PLY file
     * @param {File} file - Image file to upload
     * @returns {Promise<{task_id: string, ply_filename: string, status: string}>}
     */
    async uploadImage(file) {
        const formData = new FormData()
        formData.append('file', file)

        const response = await axios.post(`${API_BASE_URL}/upload`, formData, {
            headers: {
                'Content-Type': 'multipart/form-data'
            }
        })

        return response.data
    },

    /**
     * Generate PLY file from OSS URL
     * @param {string} url - Aliyun OSS URL to image
     * @returns {Promise<{task_id: string, ply_filename: string, status: string}>}
     */
    async generateFromOssUrl(url) {
        const response = await axios.post(`${API_BASE_URL}/generate_from_oss_url`, { url })
        return response.data
    },

    /**
     * Get PLY file URL
     * @param {string} filename - PLY filename
     * @returns {string} URL to PLY file
     */
    getPlyUrl(filename) {
        return `${API_BASE_URL}/ply/${filename}`
    },

    /**
     * Get task status
     * @param {string} taskId - Task ID
     * @returns {Promise<{status: string, ply_filename?: string, error?: string}>}
     */
    async getTaskStatus(taskId) {
        const response = await axios.get(`${API_BASE_URL}/status/${taskId}`)
        return response.data
    }
}
