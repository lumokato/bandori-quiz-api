# bandori-quiz-api

Bandori Quiz 的 FastAPI 后端服务，负责结果写入、统计查询和健康检查接口。

## 本地运行

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 3000
```

## 环境变量

```text
PORT=3000
CORS_ORIGIN=https://example.com
API_DOMAIN=api.example.com
TRAEFIK_NETWORK=proxy
POSTGRES_NETWORK=infra-postgres
POSTGRES_PASSWORD=change-me
```

## 示例访问地址

- 前端：`https://example.com`
- API：`https://api.example.com`

## 提供的接口

- `GET /healthz`
- `POST /api/save-result`
- `GET /api/stats`
- `GET /api/stats/questions`

## Portainer GitOps

- 仓库根目录提供了 `docker-compose.yml`，用于 Portainer GitOps 部署
- Portainer 的 Compose path 填 `docker-compose.yml`
- 需要在 Portainer 中提供：`CORS_ORIGIN`、`API_DOMAIN`、`TRAEFIK_NETWORK`、`POSTGRES_NETWORK`、`POSTGRES_PASSWORD`
- `docker-compose.yml` 默认通过 `infra-postgres:5432/bandori` 连接数据库，用户名固定为 `bandori`
- `docker-compose.yml` 里的 Traefik 入口点固定为 `websecure`，证书解析器根据实际选择
- 每次更新代码准备发布时，都要同步更新 `docker-compose.yml` 顶部的版本号锚点，`gitops.revision` 会随之变化并触发重新部署

## 仓库约定

- 真实环境变量不要提交，只保留 `.env.example`
- `deploy` 目录不纳入仓库
- 镜像构建时会排除 `.env`、`.venv`、缓存文件和 Git 元数据
