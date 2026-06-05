---
name: linkrag-backend
description: Generates and modifies FastAPI backend code in src/backend for the RAG knowledge base project. Follows unified response format, router layout, and auth patterns. Use when adding or changing backend APIs, routers, CRUD, or server logic in linkrag.
---

# LinkRAG Backend Skill

Apply when working in **src/backend** (FastAPI, SQLite async, JWT). Keeps code consistent with existing routers and docs.

## Scope

- **In scope**: `src/backend` only (main.py, config.py, database/, routers/, llm/, logger/, server/).
- **Out of scope**: Do not restructure or delete `src/preprocess`, `src/index`, or other repo capabilities; call them via server/ if needed.

## Response format

All APIs return `{ "code": number, "data": any, "msg": string }`.

- **Success**: Use `from routers.common import success_response` and `return success_response(data=...)`. Do not hand-write `{"code":0,...}`.
- **Failure**: `raise HTTPException(status_code=..., detail="msg")` or `detail={"msg": "..."}`. main.py normalizes to the same shape.

## Routers

- One `APIRouter` per file under `routers/`, e.g. `routers/knowledge_bases.py`.
- Prefix: `prefix="/api/xxx"` (e.g. `/api/knowledge-bases`). Align with frontend `api/modules` paths (frontend baseURL already includes `/api`).
- Register in `main.py`: `app.include_router(xxx.router)`.

## Auth

- From `routers.deps`: `require_user`, `require_admin`, `get_current_user`.
- Login required: `current_user = Depends(require_user)`.
- Admin only: `current_user = Depends(require_admin)`.
- Do not reimplement JWT parsing.

## Database

- Use `AsyncSession`, `async def`. Inject session: `db: AsyncSession = Depends(get_db)`.
- New tables/fields: extend `database/models.py` and `database/crud.py`. Keep routers thin: call crud then `return success_response(...)`.
- Commit in router when creating/updating: `await db.commit()` after crud.

## New endpoint checklist

- [ ] New router file in `routers/` or new routes in existing router.
- [ ] Router registered in `main.py` with `include_router`.
- [ ] Success returns via `success_response(data=...)`.
- [ ] Protected routes use `Depends(require_user)` or `Depends(require_admin)`.
- [ ] Path matches frontend convention (see docs/API文档.md).

## Minimal template

```python
# routers/xxx.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db, crud
from .common import success_response
from .deps import require_user

router = APIRouter(prefix="/api/xxx", tags=["XXX"])

@router.get("")
async def list_xxx(skip: int = 0, limit: int = 50, db: AsyncSession = Depends(get_db)):
    items = await crud.list_xxx(db, skip=skip, limit=limit)
    total = await crud.count_xxx(db)
    return success_response(data={"items": [...], "total": total})

@router.post("")
async def create_xxx(body: XxxCreate, db: AsyncSession = Depends(get_db), current_user=Depends(require_user)):
    one = await crud.create_xxx(db, **body.model_dump())
    await db.commit()
    return success_response(data={"id": one.id})
```

## Reference

- Full conventions: `.cursor/rules/backend-conventions.mdc`
- Dev guide and startup: `docs/后端开发文档.md`
- API list: `docs/API文档.md`
- Architecture: `docs/开发框架说明.md`
