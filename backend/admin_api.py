"""Authentication and operational controls for the TruthLens console."""

import hmac
import json
import re
import sqlite3
import threading
import time
from collections import OrderedDict
from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, Request, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from . import admin_store as store, storage


router = APIRouter()
attempts = OrderedDict()
attempt_lock = threading.Lock()
DUMMY_HASH = store.password_hash("invalid-account")


def current_account(request):
    if not hasattr(request.state, "account"):
        request.state.account = store.session_account(request.cookies.get(store.COOKIE, ""))
    return request.state.account


def require_account(request, *, admin=False):
    account = current_account(request)
    if not account:
        raise HTTPException(401, "请先登录真鉴。")
    if admin and account["role"] != "admin":
        raise HTTPException(403, "此功能需要管理员权限。")
    return account


def limit_attempts(request, username):
    address = request.client.host if request.client else ""
    now = time.monotonic()
    checks = [(address, 45), ((address, username.casefold()), 10)]
    with attempt_lock:
        for key, limit in checks:
            times = [value for value in attempts.get(key, []) if now - value < 300]
            if len(times) >= limit:
                raise HTTPException(429, "尝试次数较多，请稍后再试。")
            attempts[key] = times + [now]
            attempts.move_to_end(key)
        while len(attempts) > 4096:
            attempts.popitem(last=False)


class Credentials(BaseModel):
    username: str = Field(min_length=2, max_length=32)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("username", mode="before")
    @classmethod
    def clean_username(cls, name):
        if not isinstance(name, str) or not re.fullmatch(r"[\w.-]{2,32}", name.strip()):
            raise ValueError("用户名须为 2–32 个字，可使用汉字、字母、数字、点、下划线或横线。")
        return name.strip()


class Setup(Credentials):
    token: str = Field(min_length=10, max_length=128)


def set_session(response, request, token):
    response.set_cookie(store.COOKIE, token, httponly=True, samesite="strict",
                        secure=request.url.scheme == "https", max_age=store.SESSION_SECONDS, path="/")


def create_account(body, request, response, *, setup=False):
    limit_attempts(request, body.username)
    digest = store.password_hash(body.password)
    with store.connection(write=True) as db:
        if setup:
            if store.admin_exists(db):
                raise HTTPException(409, "管理员已经初始化。")
            try:
                expected = store.setup_token_path().read_text(encoding="ascii").strip()
            except OSError:
                raise HTTPException(503, "部署端尚未生成初始化码。") from None
            if not expected or not hmac.compare_digest(body.token.strip().encode(), expected.encode()):
                raise HTTPException(403, "管理员初始化码无效。")
        try:
            cursor = db.execute(
                "INSERT INTO accounts(username,login_key,password,role,created_at) VALUES(?,?,?,?,?)",
                (body.username, body.username.casefold(), digest, "admin" if setup else "user", store.now()),
            )
        except sqlite3.IntegrityError:
            raise HTTPException(409, "这个用户名已被使用。") from None
        account = store.account_view(db.execute("SELECT * FROM accounts WHERE id=?", (cursor.lastrowid,)).fetchone())
        token = store.issue_session(db, account["id"], request.cookies.get(store.COOKIE, ""))
        store.add_audit(db, account, "初始化管理员" if setup else "注册账号", account["username"])
    if setup:
        store.setup_token_path().unlink(missing_ok=True)
    set_session(response, request, token)
    return {"account": account}


@router.get("/api/auth/session")
def session(request: Request):
    with store.connection() as db:
        setup_required = not store.admin_exists(db)
    return {"account": current_account(request), "setup_required": setup_required}


@router.post("/api/auth/register", status_code=201)
def register(body: Credentials, request: Request, response: Response):
    return create_account(body, request, response)


@router.post("/api/auth/setup", status_code=201)
def setup(body: Setup, request: Request, response: Response):
    return create_account(body, request, response, setup=True)


@router.post("/api/auth/login")
def login(body: Credentials, request: Request, response: Response):
    limit_attempts(request, body.username)
    with store.connection() as db:
        row = db.execute("SELECT * FROM accounts WHERE login_key=?", (body.username.casefold(),)).fetchone()
    stored = row["password"] if row else DUMMY_HASH
    valid = hmac.compare_digest(store.password_hash(body.password, stored.split(":")[0]), stored)
    if not valid or not row or not row["active"]:
        raise HTTPException(401, "用户名或密码有误，或账号已停用。")
    account = store.account_view(row)
    with store.connection(write=True) as db:
        live = db.execute("SELECT * FROM accounts WHERE id=? AND active=1", (account["id"],)).fetchone()
        if not live:
            raise HTTPException(401, "账号已停用。")
        account = store.account_view(live)
        token = store.issue_session(db, account["id"], request.cookies.get(store.COOKIE, ""))
        store.add_audit(db, account, "登录账号")
    set_session(response, request, token)
    return {"account": account}


@router.post("/api/auth/logout")
def logout(request: Request, response: Response):
    token = request.cookies.get(store.COOKIE, "")
    account = current_account(request)
    if token:
        with store.connection(write=True) as db:
            db.execute("DELETE FROM sessions WHERE digest=?", (store.token_digest(token),))
            if account:
                store.add_audit(db, account, "退出登录")
    response.delete_cookie(store.COOKIE, path="/")
    return {"ok": True}


class Thresholds(BaseModel):
    whole_threshold: float = Field(ge=0.01, le=1)
    fused_threshold: float = Field(ge=0.01, le=1)
    fused_photo_threshold: float = Field(ge=0.01, le=1)
    daf_signal_threshold: float = Field(ge=0.01, le=1)
    daf_box_threshold: float = Field(ge=0.01, le=1)
    whole_weight: int = Field(ge=0, le=100)
    fused_weight: int = Field(ge=0, le=100)
    daf_weight: int = Field(ge=0, le=100)
    retention_days: int = Field(ge=0, le=3650)

    @model_validator(mode="after")
    def validate_rules(self):
        if self.whole_weight + self.fused_weight + self.daf_weight != 100:
            raise ValueError("三项权重之和必须为 100。")
        if self.daf_box_threshold < self.daf_signal_threshold:
            raise ValueError("DAF 黄框阈值不能低于候选阈值。")
        return self


class ReleaseRequest(Thresholds):
    base_version: int = Field(ge=1)


class RetentionRequest(BaseModel):
    retention_days: int = Field(ge=0, le=3650)
    base_version: int = Field(ge=1)


def publish_settings(db, account, values, operation, base_version):
    latest = db.execute("SELECT MAX(id) FROM settings").fetchone()[0]
    if base_version is not None and latest != base_version:
        raise HTTPException(409, "配置已有更新，请刷新后重试。")
    cursor = db.execute("INSERT INTO settings(body,actor,created_at) VALUES(?,?,?)",
                        (json.dumps(values), account["username"], store.now()))
    store.add_audit(db, account, operation, "版本 " + str(cursor.lastrowid))
    return store.settings_row(db.execute("SELECT * FROM settings WHERE id=?", (cursor.lastrowid,)).fetchone())


@router.get("/api/admin/settings")
def settings(request: Request):
    require_account(request, admin=True)
    with store.connection() as db:
        versions = [store.settings_row(row) for row in db.execute("SELECT * FROM settings ORDER BY id DESC LIMIT 20")]
    return {"current": versions[0], "versions": versions}


@router.put("/api/admin/settings")
def update_settings(body: ReleaseRequest, request: Request):
    account = require_account(request, admin=True)
    with store.connection(write=True) as db:
        current = store.settings_row(db.execute("SELECT * FROM settings ORDER BY id DESC LIMIT 1").fetchone())
        values = body.model_dump(exclude={"base_version", "retention_days"})
        values["retention_days"] = current["values"]["retention_days"]
        return publish_settings(db, account, values, "发布检测配置", body.base_version)


@router.put("/api/admin/retention")
def update_retention(body: RetentionRequest, request: Request):
    account = require_account(request, admin=True)
    with store.connection(write=True) as db:
        current = store.settings_row(db.execute("SELECT * FROM settings ORDER BY id DESC LIMIT 1").fetchone())
        values = {**current["values"], "retention_days": body.retention_days}
        return publish_settings(db, account, values, "更新报告保留期限", body.base_version)


@router.post("/api/admin/settings/{version}/restore")
def restore_settings(version: int, request: Request):
    account = require_account(request, admin=True)
    with store.connection(write=True) as db:
        row = db.execute("SELECT * FROM settings WHERE id=?", (version,)).fetchone()
        if not row:
            raise HTTPException(404, "没有这个配置版本。")
        current = store.settings_row(db.execute("SELECT * FROM settings ORDER BY id DESC LIMIT 1").fetchone())
        values = {**store.settings_row(row)["values"], "retention_days": current["values"]["retention_days"]}
        return publish_settings(db, account, values, f"恢复检测配置 {version}", None)


@router.get("/api/admin/accounts")
def accounts(request: Request, q: str = Query(default="", max_length=32)):
    require_account(request, admin=True)
    with store.connection() as db:
        rows = db.execute("SELECT * FROM accounts WHERE instr(login_key,?)>0 ORDER BY id DESC LIMIT 200",
                          (q.strip().casefold(),)).fetchall()
    return [store.account_view(row) for row in rows]


class AccountChange(BaseModel):
    role: Literal["user", "admin"]
    active: bool


@router.patch("/api/admin/accounts/{account_id}")
def change_account(account_id: int, body: AccountChange, request: Request):
    account = require_account(request, admin=True)
    with store.connection(write=True) as db:
        if not db.execute("SELECT 1 FROM accounts WHERE id=? AND role='admin' AND active=1", (account["id"],)).fetchone():
            raise HTTPException(403, "此功能需要管理员权限。")
        row = db.execute("SELECT * FROM accounts WHERE id=?", (account_id,)).fetchone()
        if not row:
            raise HTTPException(404, "账号不存在。")
        if account_id == account["id"] and (body.role != "admin" or not body.active):
            raise HTTPException(409, "请由另一位管理员调整你的账号。")
        db.execute("UPDATE accounts SET role=?,active=? WHERE id=?", (body.role, body.active, account_id))
        if not body.active:
            db.execute("DELETE FROM sessions WHERE account_id=?", (account_id,))
        store.add_audit(db, account, "更新账号权限", row["username"] + " / " +
                        ("管理员" if body.role == "admin" else "普通用户") + (" / 已启用" if body.active else " / 已停用"))
        return store.account_view(db.execute("SELECT * FROM accounts WHERE id=?", (account_id,)).fetchone())


Category = Literal["教学作业", "电商凭证", "新闻素材", "企业文件", "日常生活"]
State = Literal["draft", "published", "archived"]


def https_link(value):
    try:
        url = urlsplit(value.strip())
        if url.scheme == "https" and url.hostname and not url.username and not url.password and not re.search(r"[\s\\]", value):
            return value.strip()
    except ValueError:
        pass
    raise ValueError("请填写一个有效的 HTTPS 来源链接。")


class RelatedSource(BaseModel):
    label: str = Field(min_length=1, max_length=80)
    url: str = Field(max_length=1000)

    _https = field_validator("url")(https_link)


class CaseSource(BaseModel):
    publisher: str = Field(min_length=1, max_length=100)
    date: str = Field(default="", max_length=30)
    url: str = Field(max_length=1000)
    label: str | None = Field(default=None, max_length=80)
    related: RelatedSource | None = None

    _https = field_validator("url")(https_link)


class CaseItem(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    title: str = Field(min_length=2, max_length=120)
    category: Category
    kind: Literal["真实案例", "实地研究"]
    scenario: str = Field(min_length=1, max_length=1800)
    next: str = Field(min_length=1, max_length=1800)
    source: CaseSource
    status: State


class KnowledgeItem(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    title: str = Field(min_length=2, max_length=120)
    snippet: str = Field(min_length=1, max_length=1800)
    url: str = Field(max_length=1000)
    date: str = Field(default="", max_length=30)
    action: Literal["pause", "callback", "protect", "account", "source"] = "source"
    workflow: bool = False
    status: State

    _https = field_validator("url")(https_link)


@lru_cache(maxsize=1)
def default_cases():
    return json.loads(Path(__file__).with_name("verification_cases.json").read_text(encoding="utf-8"))


@router.get("/api/verification-cases")
def public_cases():
    return store.catalog_entries("cases", default_cases(), published_only=True)


@router.get("/api/admin/catalog/{kind}")
def catalog(kind: Literal["cases", "knowledge"], request: Request):
    require_account(request, admin=True)
    from .rag import CORPUS

    return store.catalog_entries(kind, default_cases() if kind == "cases" else CORPUS)


def save_catalog(kind, item_id, body, account):
    with store.connection(write=True) as db:
        db.execute(
            "INSERT INTO catalog VALUES(?,?,?,?,?) ON CONFLICT(kind,item_id) DO UPDATE SET "
            "body=excluded.body,status=excluded.status,updated_at=excluded.updated_at",
            (kind, item_id, json.dumps(body.model_dump(exclude={"status"}), ensure_ascii=False), body.status, store.now()),
        )
        operation = {"published": "发布", "draft": "保存草稿", "archived": "下架"}[body.status]
        store.add_audit(db, account, operation + ("案例" if kind == "cases" else "知识条目"), body.title)
    return {"id": item_id}


@router.put("/api/admin/catalog/cases/{item_id}")
def save_case(item_id: str, body: CaseItem, request: Request):
    account = require_account(request, admin=True)
    return save_catalog("cases", valid_item_id(item_id), body, account)


@router.put("/api/admin/catalog/knowledge/{item_id}")
def save_knowledge(item_id: str, body: KnowledgeItem, request: Request):
    account = require_account(request, admin=True)
    return save_catalog("knowledge", valid_item_id(item_id), body, account)


def valid_item_id(item_id):
    if item_id == "new":
        return uuid4().hex
    if not re.fullmatch(r"[A-Za-z0-9-]{1,48}", item_id):
        raise HTTPException(422, "条目标识无效。")
    return item_id


@router.get("/api/admin/data")
def data(request: Request):
    require_account(request, admin=True)
    from . import detector, fused_image, daf_image
    from bootstrap import ROOT

    def release(filename, fallback, section=None):
        try:
            info = json.loads((ROOT / "models" / filename).read_text(encoding="utf-8"))
            return (info.get(section) or info).get("version", fallback) if section else info.get("version", fallback)
        except (OSError, ValueError, TypeError):
            return fallback

    detectors = [
        {"name": "整图生成检测", "version": release("active-domain.json", "本地整图检测模型", "general_head"),
         "available": detector.available("image")},
        {"name": "FUSED 局部重绘", "version": "OpenSDID / e8580eb", "available": fused_image.available()},
        {"name": "DAF 文字编辑", "version": "Faster R-CNN / SRNet", "available": daf_image.available()},
        {"name": "语音合成检测", "version": release("active-audio.json", "本地声音模型"), "available": detector.available("audio")},
        {"name": "视频合成检测", "version": release("active-video.json", "本地视频模型"), "available": detector.available("video")},
    ]
    with store.connection() as db:
        totals = db.execute("SELECT COUNT(*) AS accounts, SUM(CASE WHEN active=1 THEN 1 ELSE 0 END) AS enabled FROM accounts").fetchone()
        logs = [dict(row) for row in db.execute("SELECT id,actor,operation,target,created_at FROM audit ORDER BY id DESC LIMIT 150")]
    with storage.connection() as db:
        reports = db.execute("SELECT COUNT(*) FROM cases").fetchone()[0]
    return {"accounts": totals["accounts"], "active_accounts": totals["enabled"] or 0,
            "reports": reports, "logs": logs, "detectors": detectors}
