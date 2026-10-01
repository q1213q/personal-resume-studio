"""Shared, standard-library-only checks for the included resume starter."""
import json
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

PREFIX = "window.RESUME_DATA = "
ARRAY_FIELDS = {
    "directions": ("title", "detail"),
    "metrics": ("value", "label", "context"),
    "experience": ("period", "organization", "role", "location"),
    "projects": ("title", "category", "description", "url"),
    "skills": ("name", "detail"),
    "education": ("school", "detail"),
    "contact": ("label", "url"),
}


def read_profile(path):
    text = Path(path).read_text(encoding="utf-8-sig").strip()
    if Path(path).suffix == ".js":
        if not text.startswith(PREFIX) or not text.endswith(";"):
            raise ValueError("profile.js 必须使用 window.RESUME_DATA = {...}; 格式。")
        text = text[len(PREFIX):-1]
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("资料必须是一个 JSON 对象。")
    return data


def write_profile(path, data):
    Path(path).write_text(PREFIX + json.dumps(data, ensure_ascii=False, indent=2) + ";\n", encoding="utf-8")


def strings(value, prefix=""):
    if isinstance(value, str):
        yield prefix, value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from strings(item, f"{prefix}.{key}" if prefix else key)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from strings(item, f"{prefix}[{index}]")


def local_asset(root, value):
    parsed = urlsplit(value)
    if parsed.scheme or parsed.netloc or not parsed.path or "\\" in parsed.path:
        raise ValueError("必须使用项目内的相对文件路径。")
    path = Path(unquote(parsed.path))
    if path.is_absolute():
        raise ValueError("不能使用绝对路径。")
    root = Path(root).resolve()
    target = (root / path).resolve()
    if root not in target.parents:
        raise ValueError("资源不能越出项目目录。")
    return target


def validate(data, root=None, final=False):
    errors, warnings = [], []

    def check_text(value, label, required=False):
        if not isinstance(value, str):
            errors.append(f"{label} 必须是文字。")
        elif required and not value.strip():
            errors.append(f"{label} 不能为空。")

    for key in ("name", "role", "intro"):
        check_text(data.get(key), key, True)
    for key in ("location", "photo", "photoAlt"):
        if key in data:
            check_text(data[key], key)
    if not isinstance(data.get("draft"), bool):
        errors.append("draft 必须为 true 或 false。")
    if data.get("layout", "overlay") not in ("overlay", "split", "type"):
        errors.append("layout 只能是 overlay、split 或 type。")
    headline = data.get("headline")
    if not isinstance(headline, list) or len(headline) != 2:
        errors.append("headline 必须包含两行标题。")
    else:
        for i, value in enumerate(headline):
            check_text(value, f"headline[{i}]", True)
    about = data.get("about", [])
    if not isinstance(about, list):
        errors.append("about 必须是段落数组。")
    else:
        for i, value in enumerate(about):
            check_text(value, f"about[{i}]", True)

    urls = []
    for key, fields in ARRAY_FIELDS.items():
        rows = data.get(key, [])
        if not isinstance(rows, list):
            errors.append(f"{key} 必须是数组。")
            continue
        for i, row in enumerate(rows):
            label = f"{key}[{i}]"
            if not isinstance(row, dict):
                errors.append(f"{label} 必须是对象。")
                continue
            for field in fields:
                optional = field in ("url", "location", "category") and key != "contact"
                check_text(row.get(field, ""), f"{label}.{field}", not optional)
            if key == "experience":
                points = row.get("points", [])
                if not isinstance(points, list):
                    errors.append(f"{label}.points 必须是文字数组。")
                else:
                    for j, value in enumerate(points):
                        check_text(value, f"{label}.points[{j}]", True)
            if isinstance(row.get("url"), str) and row["url"]:
                urls.append((f"{label}.url", row["url"]))

    theme = data.get("theme", {})
    if not isinstance(theme, dict):
        errors.append("theme 必须是对象。")
    else:
        for key, value in theme.items():
            if key in ("accent", "background") and (not isinstance(value, str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", value)):
                errors.append(f"theme.{key} 应类似 #c3a7e8。")
    resume = data.get("resume", {})
    if not isinstance(resume, dict):
        errors.append("resume 必须是对象。")
        resume = {}
    for key in ("file", "filename"):
        check_text(resume.get(key, ""), f"resume.{key}")
    filename = resume.get("filename", "")
    if isinstance(filename, str) and any(c in filename for c in ("/", "\\", "\n", "\r")):
        errors.append("resume.filename 只能填写文件名。")
    for label, value in (("photo", data.get("photo", "")), ("resume.file", resume.get("file", ""))):
        if not isinstance(value, str) or not value:
            continue
        try:
            target = local_asset(root or Path.cwd(), value)
            if root is not None and not target.is_file():
                errors.append(f"{label} 对应文件不存在：{value}")
        except ValueError as exc:
            errors.append(f"{label}：{exc}")

    for label, value in urls:
        try:
            if any(ord(c) < 32 for c in value) or "\\" in value or value.startswith("//"):
                raise ValueError("链接格式无效。")
            parsed = urlsplit(value)
            if parsed.scheme:
                if parsed.scheme.lower() not in ("https", "http", "mailto", "tel"):
                    raise ValueError("只支持 http、https、mailto 和 tel 链接。")
                if parsed.scheme.lower() in ("https", "http") and not parsed.netloc:
                    raise ValueError("网站链接缺少域名。")
            elif parsed.path:
                target = local_asset(root or Path.cwd(), value)
                if root is not None and not target.is_file():
                    errors.append(f"{label} 对应本地文件不存在：{value}")
        except ValueError as exc:
            errors.append(f"{label}：{exc}")

    example = Path(__file__).resolve().parents[1] / "assets/profile.example.json"
    placeholders = {v for k, v in strings(read_profile(example)) if v and k not in {"layout", "photoAlt"} and not k.startswith("theme.")}
    pending = [k for k, value in strings(data) if value in placeholders or re.search(r"待补充|待核对|\bTODO\b|\bTBD\b", value, re.I)]
    if pending:
        message = "仍有示例或待补充内容：" + "、".join(pending)
        (errors if final else warnings).append(message)
    if data.get("draft"):
        (errors if final else warnings).append("draft=true：当前是草稿；核对真实内容后再设为 false。")
    if not resume.get("file"):
        warnings.append("未提供下载文件，将显示完整履历阅读入口，可从阅读页打印。")
    return errors, warnings


def report(errors, warnings):
    for message in errors:
        print("错误：" + message)
    for message in warnings:
        print("提示：" + message)
