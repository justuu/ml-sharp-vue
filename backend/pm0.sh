#!/bin/bash
# 先停止已有的
pm2 stop main-sharp
pm2 delete main-sharp

# 创建 pm2 配置文件
cat > ecosystem-sharp.config.js << 'EOF'
module.exports = {
  apps: [{
    name: 'main-sharp',
    script: '/root/backend/main.py',
    interpreter: '/root/miniconda3/envs/sharp/bin/python',
    env: {
      HF_ENDPOINT: 'https://hf-mirror.com',
      CUDA_VISIBLE_DEVICES: '0'
    },
    log_date_format: 'YYYY-MM-DD HH:mm:ss',
    error_file: 'logs/sharp/err.log',
    out_file: 'logs/sharp/out.log'
  }]
}
EOF

# 启动
pm2 start ecosystem-sharp.config.js