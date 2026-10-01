#!/usr/bin/env python3
"""Check published bytes against a local manifest; not a browser or speed audit."""
import argparse
import json
import shutil
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote, urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from release_tools import file_digest, read_manifest


def base_url(value):
    parsed = urlsplit(value)
    if (parsed.scheme not in {"http", "https"} or not parsed.hostname
            or parsed.username is not None or parsed.password is not None
            or parsed.query or parsed.fragment
            or any(ord(c) < 33 or ord(c) == 127 for c in value)):
        raise ValueError("base-url 须为不含凭据、查询参数和锚点的 HTTP(S) 目录网址。")
    parsed.port  # Validate a supplied port.
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path.rstrip("/") + "/", "", ""))


class LimitedRedirects(HTTPRedirectHandler):
    max_redirections = 5

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        target = urlsplit(newurl)
        if (target.scheme not in {"http", "https"} or target.username is not None
                or target.password is not None):
            raise ValueError("重定向到了非公开 HTTP(S) 地址。")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch_urllib(url, target, timeout, limit):
    request = Request(url, headers={"User-Agent": "ResumeSiteVerifier/1.0", "Accept-Encoding": "identity"})
    started = time.monotonic()
    try:
        response = build_opener(LimitedRedirects()).open(request, timeout=timeout)
    except HTTPError as error:
        response = error  # Retain HTTP status and the error document for diagnosis.
    with response, target.open("wb") as output:
        count = 0
        while True:
            if time.monotonic() - started > timeout:
                raise TimeoutError("响应超过时间上限。")
            chunk = response.read(65536)
            if not chunk:
                break
            count += len(chunk)
            if count > limit:
                raise ValueError("响应远大于预期文件，停止下载；可能返回了错误资源。")
            output.write(chunk)
        return {"status": response.status, "final_url": response.geturl(), "seconds": round(time.monotonic() - started, 3)}


def fetch_curl(url, target, timeout, limit):
    # No shell, no credentials, no insecure TLS flags, no change to proxy settings.
    command = [
        "curl", "--disable", "--silent", "--show-error", "--location",
        "--max-redirs", "5", "--proto", "=http,https", "--proto-redir", "=http,https",
        "--max-time", str(timeout), "--max-filesize", str(limit),
        "--header", "Accept-Encoding: identity", "--user-agent", "ResumeSiteVerifier/1.0",
        "--output", str(target), "--write-out", "%{http_code}\n%{url_effective}\n%{time_total}", url,
    ]
    result = subprocess.run(command, capture_output=True, text=True, timeout=timeout + 5)
    if result.returncode:
        raise ValueError(f"curl 失败（{result.returncode}）：{result.stderr.strip()[:500]}")
    status, final_url, seconds = result.stdout.strip().split("\n", 2)
    return {"status": int(status), "final_url": final_url, "seconds": round(float(seconds), 3)}


def main():
    parser = argparse.ArgumentParser(description="核对公开站点文件的 HTTP 状态、字节数与 SHA-256；不代替浏览器交互。")
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--report", type=Path, help="可选 JSON 报告；选择新路径并放在公开目录之外")
    parser.add_argument("--timeout", type=float, default=20, help="单个文件超时秒数，默认 20")
    parser.add_argument("--transport", choices=("auto", "curl", "urllib"), default="auto")
    args = parser.parse_args()
    try:
        base = base_url(args.base_url)
        manifest = read_manifest(args.manifest)
        if not 0 < args.timeout <= 300:
            raise ValueError("timeout 必须在 0 到 300 秒之间。")
        if args.report and (args.report.exists() or args.report.is_symlink()):
            raise ValueError("报告路径已存在；请选择新路径，保留此前测试证据。")
        transport = args.transport
        if transport == "auto":
            transport = "curl" if shutil.which("curl") else "urllib"
        if transport == "curl" and not shutil.which("curl"):
            raise ValueError("未安装 curl；可使用 --transport urllib。")
        fetch = fetch_curl if transport == "curl" else fetch_urllib
        report = {"schema_version": 1, "checked_at": datetime.now(timezone.utc).isoformat(),
                  "base_url": base, "transport": transport, "passed": True, "files": [],
                  "scope": "HTTP 文件一致性；不包含浏览器交互、真人手机或跨地区速度。"}
        with tempfile.TemporaryDirectory(prefix="site-verify-") as scratch:
            for index, expected in enumerate(manifest["files"]):
                url = base + quote(expected["path"], safe="/")
                actual = {"path": expected["path"], "url": url,
                          "expected_bytes": expected["bytes"], "expected_sha256": expected["sha256"]}
                try:
                    target = Path(scratch) / str(index)
                    actual.update(fetch(url, target, args.timeout, max(expected["bytes"] + 65536, 1024 * 1024)))
                    size, digest = file_digest(target)
                    actual.update({"bytes": size, "sha256": digest})
                    actual["passed"] = actual["status"] == 200 and size == expected["bytes"] and digest == expected["sha256"]
                except (OSError, ValueError, TimeoutError, subprocess.SubprocessError) as exc:
                    actual.update({"passed": False, "error": str(exc)[:800]})
                report["files"].append(actual)
                report["passed"] = report["passed"] and actual["passed"]
                print(f"{'通过' if actual['passed'] else '失败'}：{expected['path']} | HTTP {actual.get('status', '未知')} | {actual.get('seconds', '?')}s")
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            with args.report.open("x", encoding="utf-8") as output:
                output.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
            print(f"报告：{args.report}")
        print("文件一致性检查完成；请继续浏览器验收。" if report["passed"] else "有文件不一致或请求失败，请查看报告／网络路径后修复。")
        return 0 if report["passed"] else 1
    except (OSError, ValueError) as exc:
        print(f"校验失败：{exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
