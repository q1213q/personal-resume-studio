#!/usr/bin/env python3
"""Validate a packed release, then invoke the official HSK CLI in the foreground."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

from release_tools import file_digest, public_path, read_manifest, source_file

PACKAGE = "@aweray/hsk-cli@0.7.24"


def check_release(release):
    """Reject drift and extra files before a directory upload can expose them."""
    if release.is_symlink():
        raise ValueError("发布目录不能是符号链接。")
    root = release.resolve()
    site = root / "site"
    manifest_path = root / "manifest.json"
    if site.is_symlink() or manifest_path.is_symlink() or not site.is_dir():
        raise ValueError("需要 pack_site.py 生成的 site/ 和 manifest.json，不能是符号链接。")
    manifest = read_manifest(manifest_path)
    if Path(manifest["entry"]).suffix.lower() not in {".html", ".htm"}:
        raise ValueError("入口必须是 HTML 文件。")
    expected = {f["path"] for f in manifest["files"]}
    actual = set()
    for path in site.rglob("*"):
        name = public_path(path.relative_to(site).as_posix())
        if path.is_symlink():
            raise ValueError(f"发布目录不能包含符号链接：{name}")
        if path.is_file():
            actual.add(name)
        elif not path.is_dir():
            raise ValueError(f"发布目录包含非普通文件：{name}")
    if actual != expected:
        raise ValueError("site/ 文件与清单不一致；请重新打包，不上传后来混入的文件。")
    for item in manifest["files"]:
        size, digest = file_digest(source_file(site, item["path"]))
        if size != item["bytes"] or digest != item["sha256"]:
            raise ValueError(f"打包后文件发生变化，请重新打包：{item['path']}")
    return site, manifest


def cli_prefix():
    installed = shutil.which("hsk-cli")
    if installed:
        return [installed]
    node, npx = shutil.which("node"), shutil.which("npx")
    if not node or not npx:
        raise ValueError("未找到 hsk-cli 或 Node.js/npx；请按 references/hsk-publish.md 准备官方工具。")
    version = subprocess.run([node, "--version"], capture_output=True, text=True, check=True)
    match = re.match(r"v?(\d+)", version.stdout.strip())
    if not match or int(match.group(1)) < 16:
        raise ValueError("花生壳 npm 工具要求 Node.js 16+；建议使用受支持的 LTS 版本。")
    return [npx, "--yes", PACKAGE]


def first_json(output):
    # Native commands emit one-line JSON; doctor may emit pretty-printed JSON.
    try:
        result = json.loads(output)
        if isinstance(result, dict):
            return result
    except ValueError:
        pass
    for line in output.splitlines():
        try:
            result = json.loads(line)
            if isinstance(result, dict):
                return result
        except ValueError:
            continue
    raise ValueError("官方工具没有返回可识别的 JSON；按输出排障，不能继续上传。")


def inspect_command(command, env, payload=None):
    # Only setup/wizard output is captured. Upload output must remain live so the
    # agent can hand off a claim URL while the official process is still waiting.
    result = subprocess.run(command, input=payload, stdout=subprocess.PIPE,
                            text=True, encoding="utf-8", env=env)
    # Reserve stdout for the eventual upload result. Setup JSON goes to stderr
    # so it cannot be mistaken for a successful publication by the caller.
    print(result.stdout, end="", file=sys.stderr, flush=True)
    data = first_json(result.stdout)
    if result.returncode != 0 or data.get("success") is not True:
        raise ValueError("官方准备步骤未完成；请按上方提示处理，再继续。")
    return data


def main(argv=None):
    parser = argparse.ArgumentParser(description="校验发布包，调用花生壳向导与文件托管；登录认领由官方页面完成。")
    parser.add_argument("--release", type=Path, required=True, help="pack_site.py 的输出目录，不是源码或 Skill 目录")
    parser.add_argument("--dry-run", action="store_true", help="仅本地校验，不下载工具、不联网、不上传")
    parser.add_argument("--agent", help="实际调用方标识，如 codex、claude、cursor；不可冒用其他工具")
    parser.add_argument("--channel", choices=["rich", "none"], default="rich", help="rich 可向用户展示链接；none 为纯终端")
    parser.add_argument("--wizard-answers", type=Path, help="按最新向导 answer_template 填写的 JSON，留在私人项目中")
    args = parser.parse_args(argv)
    try:
        site, manifest = check_release(args.release)
        print(f"发布包校验通过：{len(manifest['files'])} 个文件，照片与附件字节未改变。", file=sys.stderr, flush=True)
        if args.dry_run:
            print(json.dumps({"status": "checked_only", "uploaded": False,
                              "entry": manifest["entry"], "files": len(manifest["files"])}, ensure_ascii=False))
            return 0
        if not args.agent or not re.fullmatch(r"[a-z0-9][a-z0-9-]*", args.agent):
            raise ValueError("实际上传需要 --agent 指定当前 AI 工具标识。")
        answers = None
        if args.wizard_answers:
            if site == args.wizard_answers.resolve() or site in args.wizard_answers.resolve().parents:
                raise ValueError("向导答案不能保存在公开的 site/ 目录中。")
            answers = args.wizard_answers.read_text(encoding="utf-8-sig")
            data = json.loads(answers)
            if not isinstance(data, dict) or not isinstance(data.get("answers"), list):
                raise ValueError("使用最新 data.answer_template 的结构填写向导答案。")
        command = cli_prefix()
        env = os.environ.copy()
        env["AI_AGENT"] = args.agent
        context = json.dumps({"task_goal": "share_file", "agent_channel": args.channel})
        print("[发布准备] 官方自检", file=sys.stderr, flush=True)
        inspect_command(command + ["doctor", "--format", "json"], env)
        wizard = command + ["context", "wizard", "--context", context, "--format", "json"]
        print("[发布准备] 官方向导；下方 JSON 是准备状态，不是上传结果", file=sys.stderr, flush=True)
        result = inspect_command(wizard, env)
        if answers is not None:
            result = inspect_command(wizard + ["--stdin"], env, answers)
        data = result.get("data", {})
        if not isinstance(data, dict) or not isinstance(data.get("ask"), list):
            raise ValueError("向导格式已变化，请核实当前官方文档；尚未上传。")
        recommendations = data.get("recommendations", [])
        if data["ask"]:
            print("尚未上传。由 AI 按 data.ask/options 补齐可推断的信息，仅将必要选择交给用户，再用 --wizard-answers 继续。", file=sys.stderr)
            return 2
        if not isinstance(recommendations, list) or not any(
                isinstance(r, dict) and isinstance(r.get("next"), str)
                and re.match(r"^hsk-cli file-hosting(?:\s|$)", r["next"])
                for r in recommendations):
            print("尚未上传。请按向导推荐先完成当前步骤；本脚本只执行静态文件托管。", file=sys.stderr)
            return 2
        claim_channel = data.get("claim_channel", {})
        can_auto_claim = isinstance(claim_channel, dict) and (
            claim_channel.get("logged_in") is True or claim_channel.get("api_key_configured") is True)
        if not can_auto_claim and any(
                isinstance(r, dict) and str(r.get("next", "")).startswith("hsk-cli auth login")
                for r in recommendations):
            print("尚未上传。向导推荐先登录以归属账号；AI 应打开官方登录页交接，再运行此入口。", file=sys.stderr)
            return 2
        # Recheck after any user/setup delay. Never upload the manifest or source.
        check_release(args.release)
        print("开始官方上传。认领链接会实时显示；AI 应及时打开页面交给用户，保持当前命令前台等待。", file=sys.stderr, flush=True)
        code = subprocess.call(command + ["file-hosting", str(site), "--entry-file", manifest["entry"],
                                          "--context", context, "--format", "json"], env=env)
        print("下一步：读取官方 claimed/pending 结果，完成认领后再校验公网文件。命令返回 0 不等于网站已验收。", file=sys.stderr)
        return code
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f"发布入口未完成：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
