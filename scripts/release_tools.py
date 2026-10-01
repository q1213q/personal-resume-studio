"""Shared validation for explicit, public static-site releases (standard library)."""
import hashlib
import json
import re
from pathlib import Path, PurePosixPath

PRIVATE_NAMES = {
    "node_modules", "__pycache__", "credentials", "credentials.json",
    "auth.json", "api_key.json", "token.json", "secrets.json", "secrets.yaml",
    "id_rsa", "id_ed25519", "project-brief.md", "agents.md", "skill.md",
}


def public_path(value):
    if not isinstance(value, str) or not value or "\\" in value or ":" in value:
        raise ValueError(f"必须是使用 / 分隔的相对文件路径：{value!r}")
    parts = value.split("/")
    if any(not p or p.startswith(".") or p.lower() in PRIVATE_NAMES for p in parts):
        raise ValueError(f"路径越界、隐藏路径或常见私有文件不可发布：{value!r}")
    if any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise ValueError("路径不可包含控制字符。")
    path = PurePosixPath(value)
    if path.is_absolute() or path.suffix.lower() in {".pem", ".key", ".p12", ".pfx"}:
        raise ValueError(f"绝对路径或凭据文件不可发布：{value!r}")
    return value


def unique_paths(values):
    if not isinstance(values, list) or not values:
        raise ValueError("文件清单必须是非空 JSON 数组。")
    result, seen = [], set()
    for value in values:
        path = public_path(value)
        if path.casefold() in seen:
            raise ValueError(f"文件路径重复或仅大小写不同：{path}")
        seen.add(path.casefold())
        result.append(path)
    return sorted(result)


def file_digest(path):
    digest = hashlib.sha256()
    count = 0
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            count += len(chunk)
            digest.update(chunk)
    return count, digest.hexdigest()


def source_file(root, relative):
    current = root
    for part in PurePosixPath(public_path(relative)).parts:
        current = current / part
        if current.is_symlink():
            raise ValueError(f"文件清单不可经过符号链接：{relative}")
    if not current.is_file():
        raise ValueError(f"清单中的文件不存在：{relative}")
    current.resolve().relative_to(root)
    return current


def read_manifest(path):
    data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise ValueError("不支持的 manifest 格式。")
    files = data.get("files")
    if not isinstance(files, list) or not all(isinstance(f, dict) for f in files):
        raise ValueError("manifest.files 必须为文件对象数组。")
    paths = unique_paths([f.get("path") for f in files])
    if data.get("entry") not in paths:
        raise ValueError("manifest 中缺少入口文件。")
    for item in files:
        if type(item.get("bytes")) is not int or item["bytes"] < 0:
            raise ValueError("manifest 文件字节数无效。")
        if not isinstance(item.get("sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", item["sha256"]):
            raise ValueError("manifest 文件哈希无效。")
    return data
