#!/bin/bash
# ==========================================
# LinkRAG System Linux 一键发布部署脚本
# ==========================================

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 工作目录
PROJECT_DIR=$(pwd)
FRONTEND_DIR="${PROJECT_DIR}/src/frontend"
BACKEND_DIR="${PROJECT_DIR}/src/backend"
NGINX_CONF_DIR="/etc/nginx/conf.d"

echo -e "${BLUE}=== 开始部署 LinkRAG 系统 ===${NC}"

# ==========================================
# 1. 前置依赖检查
# ==========================================
echo -e "\n${YELLOW}[1/5] 检查系统依赖...${NC}"
command -v node >/dev/null || echo -e "${RED}未安装 Node.js, 请先安装 node 和 npm${NC}"
command -v pnpm >/dev/null || npm install -g pnpm
command -v python3 >/dev/null || echo -e "${RED}未安装 Python3, 请先安装${NC}"
command -v nginx >/dev/null || echo -e "${RED}未安装 Nginx, 请先安装${NC}"

# ==========================================
# 2. 部署前端 (Vue + Vite)
# ==========================================
echo -e "\n${YELLOW}[2/5] 正在构建前端项目...${NC}"
cd $FRONTEND_DIR
if [ ! -d "node_modules" ]; then
    echo -e "安装前端依赖..."
    pnpm install
fi

echo -e "打包前端代码..."
pnpm run build

if [ $? -eq 0 ]; then
    echo -e "${GREEN}前端构建成功，产物位于: ${FRONTEND_DIR}/dist${NC}"
else
    echo -e "${RED}前端构建失败!${NC}"
    exit 1
fi

# ==========================================
# 3. 部署后端 (Python + FastAPI)
# ==========================================
echo -e "\n${YELLOW}[3/5] 正在配置后端环境...${NC}"
cd $BACKEND_DIR

if [ ! -d ".venv" ]; then
    echo -e "创建虚拟环境..."
    python3 -m venv .venv
fi

echo -e "激活虚拟环境并安装依赖..."
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 生成后端 systemd 服务文件
SERVICE_FILE="/etc/systemd/system/linkrag-backend.service"
echo -e "\n${YELLOW}[4/5] 配置后端 systemd 服务... (可能需要 sudo 权限)${NC}"

cat <<EOF | sudo tee $SERVICE_FILE
[Unit]
Description=LinkRAG FastAPI Backend
After=network.target

[Service]
User=$USER
WorkingDirectory=$BACKEND_DIR
Environment="PATH=$BACKEND_DIR/.venv/bin"
ExecStart=$BACKEND_DIR/.venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000 --workers 4
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable linkrag-backend
sudo systemctl restart linkrag-backend
echo -e "${GREEN}后端服务已重启并设置为开机自启${NC}"

# ==========================================
# 4. 配置 Nginx
# ==========================================
echo -e "\n${YELLOW}[5/5] 配置 Nginx 代理... (可能需要 sudo 权限)${NC}"
NGINX_CONF="/etc/nginx/conf.d/linkrag.conf"

cat <<EOF | sudo tee $NGINX_CONF
server {
    listen 80;
    server_name _; # 请修改为实际域名或IP

    # 前端静态文件
    location / {
        root $FRONTEND_DIR/dist;
        index index.html;
        try_files \$uri \$uri/ /index.html;
    }

    # 后端API代理
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # 允许WebSocket和较长的超时时间（为对接大模型准备）
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 300;
    }
}
EOF

sudo nginx -t && sudo systemctl restart nginx
if [ $? -eq 0 ]; then
    echo -e "${GREEN}Nginx 配置并重启成功！${NC}"
else
    echo -e "${RED}Nginx 配置错误，请手动检查。${NC}"
fi

# ==========================================
echo -e "\n${GREEN}==========================================${NC}"
echo -e "${GREEN}🎉 部署完成！${NC}"
echo -e "前端目录: ${FRONTEND_DIR}/dist"
echo -e "后端目录: ${BACKEND_DIR}"
echo -e "查看后端日志: sudo journalctl -u linkrag-backend -f"
echo -e "请在浏览器中访问这台服务器的 IP 地址查看系统"
echo -e "${GREEN}==========================================${NC}"
