#!/bin/bash
# ==========================================
# LinkRAG Linux 一体化部署脚本（无 Nginx）
# 前端打包后由 FastAPI 直接托管
# ==========================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PROJECT_DIR=$(pwd)
FRONTEND_DIR="${PROJECT_DIR}/src/frontend"
BACKEND_DIR="${PROJECT_DIR}/src/backend"
FRONTEND_DIST_TARGET="${BACKEND_DIR}/frontend_dist"
SERVICE_NAME="linkrag-allinone"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

echo -e "${BLUE}=== 开始一体化部署 LinkRAG（无 Nginx） ===${NC}"

echo -e "\n${YELLOW}[1/5] 检查依赖...${NC}"
command -v python3 >/dev/null || { echo -e "${RED}未安装 Python3${NC}"; exit 1; }

USE_PREBUILT_FRONTEND=false
if [ -f "${FRONTEND_DIST_TARGET}/index.html" ]; then
  USE_PREBUILT_FRONTEND=true
  echo -e "检测到已内置前端产物: ${FRONTEND_DIST_TARGET}"
else
  command -v node >/dev/null || { echo -e "${RED}未安装 Node.js，且未检测到预构建 frontend_dist${NC}"; exit 1; }
  command -v pnpm >/dev/null || npm install -g pnpm
fi

echo -e "\n${YELLOW}[2/5] 构建前端...${NC}"
if [ "$USE_PREBUILT_FRONTEND" = true ]; then
  echo -e "使用发布包内置前端产物，跳过前端构建"
else
  cd "$FRONTEND_DIR"
  if [ ! -d "node_modules" ]; then
    pnpm install
  fi
  pnpm run build

  echo -e "复制前端产物到后端目录..."
  rm -rf "$FRONTEND_DIST_TARGET"
  cp -r "$FRONTEND_DIR/dist" "$FRONTEND_DIST_TARGET"
fi

echo -e "\n${YELLOW}[3/5] 配置后端环境...${NC}"
cd "$BACKEND_DIR"
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 可重复执行的 DB 同步
python migrate_db.py || true

# 修复前端静态资源权限（避免 500: Permission denied）
SERVICE_USER="$USER"
if [ -z "$SERVICE_USER" ]; then
  SERVICE_USER="$(id -un)"
fi
if [ -d "$FRONTEND_DIST_TARGET" ]; then
  sudo chown -R "$SERVICE_USER":"$SERVICE_USER" "$FRONTEND_DIST_TARGET" || true
  sudo find "$FRONTEND_DIST_TARGET" -type d -exec chmod 755 {} \;
  sudo find "$FRONTEND_DIST_TARGET" -type f -exec chmod 644 {} \;
fi

echo -e "\n${YELLOW}[4/5] 写入 systemd 服务...${NC}"
cat <<EOF | sudo tee "$SERVICE_FILE"
[Unit]
Description=LinkRAG All-in-One (FastAPI + Frontend Static)
After=network.target

[Service]
User=$USER
WorkingDirectory=$BACKEND_DIR
Environment="PATH=$BACKEND_DIR/.venv/bin"
Environment="SERVE_FRONTEND=true"
Environment="FRONTEND_DIST_DIR=$FRONTEND_DIST_TARGET"
ExecStart=$BACKEND_DIR/.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8003 --workers 2
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"
sudo systemctl restart "$SERVICE_NAME"

echo -e "\n${YELLOW}[5/5] 健康检查...${NC}"
sleep 2
if systemctl is-active --quiet "$SERVICE_NAME"; then
  echo -e "${GREEN}服务启动成功${NC}"
else
  echo -e "${RED}服务启动失败，请查看日志${NC}"
  sudo journalctl -u "$SERVICE_NAME" -n 100 --no-pager
  exit 1
fi

echo -e "\n${GREEN}==========================================${NC}"
echo -e "${GREEN}🎉 一体化部署完成（无 Nginx）${NC}"
echo -e "访问地址: http://<服务器IP>:8003"
echo -e "后端日志: sudo journalctl -u ${SERVICE_NAME} -f"
echo -e "${GREEN}==========================================${NC}"
