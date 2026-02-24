# ML-Sharp Vue 3D 可视化项目

基于 Apple ml-sharp 的 3D Gaussian Splatting 可视化 Web 应用。用户上传图片,系统自动生成 3D PLY 模型并提供交互式 3D 查看器。

## 功能特性

- 📤 **图片上传**: 支持拖拽上传和文件选择
- 🎨 **3D 生成**: 使用 Apple ml-sharp 从单张图片生成 3D Gaussian Splat
- 🎯 **3D 可视化**: 基于 Three.js 的交互式 3D 查看器
- 🎮 **相机控制**: 旋转、平移、缩放视角
- 📸 **截图导出**: 导出当前视角的渲染图片

## 技术栈

### 后端
- Python 3.13
- FastAPI
- Apple ml-sharp
- PyTorch

### 前端
- Vue 3
- Vite
- Three.js
- Axios

## 安装步骤

### 1. 后端设置

```bash
cd backend

# 创建 Conda 环境
conda create -n ml-sharp-backend python=3.12 -y

# 激活环境
conda activate ml-sharp-backend

# 安装 PyTorch (CUDA 12.8)
pip3 install torch torchvision --index-url https://download.pytorch.org/whl/cu128

# 安装依赖
pip install -r requirements.txt

# 安装 ml-sharp
pip install git+https://github.com/apple/ml-sharp.git
```

### 2. 前端设置

```bash
cd frontend

# 安装依赖
npm install
```

## 运行项目

### 启动后端服务器

```bash
cd backend
conda activate ml-sharp-backend
python main.py
```

后端将运行在 `http://localhost:8000`

### 启动前端开发服务器

```bash
cd frontend
npm run dev
```

前端将运行在 `http://localhost:5173`

## 使用说明

1. 打开浏览器访问 `http://localhost:5173`
2. 上传一张图片(支持 JPG, PNG, WebP 格式)
3. 等待系统生成 3D 模型(首次运行会自动下载模型,约 500MB)
4. 在 3D 查看器中:
   - 🖱️ **左键拖拽**: 旋转视角
   - 🖱️ **右键拖拽**: 平移视角
   - 🖱️ **滚轮**: 缩放
   - 📸 **截图按钮**: 导出当前视角
   - 🔄 **重置视角**: 恢复默认相机位置

## 配置说明

### HuggingFace 镜像

模型下载使用 HuggingFace 镜像 (`https://hf-mirror.com/`),配置在 `backend/config.py` 中。

### 模型存储

模型文件保存在 `backend/models/` 目录下,首次运行时自动下载。

### GPU 支持

- 推荐使用 CUDA GPU,处理速度 <1 秒/图片
- CPU 模式也支持,但速度较慢

## 项目结构

```
ml-sharp-vue/
├── backend/
│   ├── main.py              # FastAPI 应用入口
│   ├── config.py            # 配置文件
│   ├── ml_sharp_service.py  # ml-sharp 服务层
│   ├── requirements.txt     # Python 依赖
│   ├── models/              # 模型存储目录
│   ├── uploads/             # 上传图片目录
│   └── outputs/             # 生成的 PLY 文件目录
├── frontend/
│   ├── src/
│   │   ├── App.vue          # 主应用组件
│   │   ├── main.js          # 入口文件
│   │   ├── style.css        # 全局样式
│   │   ├── components/
│   │   │   ├── ImageUpload.vue  # 图片上传组件
│   │   │   └── PlyViewer.vue    # 3D 查看器组件
│   │   └── services/
│   │       └── api.js       # API 服务
│   ├── index.html
│   ├── vite.config.js
│   └── package.json
└── README.md
```

## API 接口

### POST /api/upload
上传图片并生成 PLY 文件

**请求**: multipart/form-data
- `file`: 图片文件

**响应**:
```json
{
  "task_id": "uuid",
  "ply_filename": "uuid.ply",
  "status": "completed"
}
```

### GET /api/ply/{filename}
获取生成的 PLY 文件

### GET /api/status/{task_id}
查询任务状态

## 许可证

本项目基于以下开源项目:
- [Apple ml-sharp](https://github.com/apple/ml-sharp)
- [Three.js](https://threejs.org/)
- [FastAPI](https://fastapi.tiangolo.com/)
- [Vue.js](https://vuejs.org/)
