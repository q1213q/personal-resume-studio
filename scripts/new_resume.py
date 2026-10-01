#!/usr/bin/env python3
"""Create a portable resume from public JSON data; never overwrite a project."""
import argparse
import shutil
import tempfile
from pathlib import Path
from profile_tools import local_asset, read_profile, report, validate, write_profile


def main():
    parser = argparse.ArgumentParser(description="用真实资料生成可直接打开的个人简历网站。")
    parser.add_argument("--data", required=True, type=Path, help="公开资料 JSON 文件")
    parser.add_argument("--out", required=True, type=Path, help="新的或空的输出目录")
    parser.add_argument("--photo", type=Path, help="可选本地肖像文件")
    parser.add_argument("--resume", type=Path, help="可选 PDF 或 DOCX 完整简历")
    parser.add_argument("--final", action="store_true", help="拒绝草稿和未替换示例")
    args = parser.parse_args()
    staging = None
    try:
        if args.out.is_symlink():
            raise ValueError("输出目录不能是符号链接。")
        out = args.out.resolve()
        if out.exists() and (not out.is_dir() or any(out.iterdir())):
            raise ValueError("输出目录非空，已停止。请选择新目录，已有项目直接编辑 profile.js。")
        data = read_profile(args.data)
        errors, _ = validate(data, final=args.final)
        if errors:
            report(errors, [])
            return 1
        copy_assets = []
        for key, override, allowed in (
            ("photo", args.photo, {".png", ".jpg", ".jpeg", ".webp", ".avif"}),
            ("resume", args.resume, {".pdf", ".docx"}),
        ):
            value = data.get("photo", "") if key == "photo" else data.get("resume", {}).get("file", "")
            source = override.resolve() if override else local_asset(args.data.resolve().parent, value) if value else None
            if source is None:
                continue
            if not source.is_file() or source.suffix.lower() not in allowed:
                raise ValueError(f"{key} 文件不存在或格式不支持：{source}")
            relative = "assets/" + ("portrait" if key == "photo" else "resume") + source.suffix.lower()
            copy_assets.append((source, relative))
            if key == "photo":
                data["photo"] = relative
            else:
                data.setdefault("resume", {})["file"] = relative
                data["resume"]["filename"] = data["resume"].get("filename") or source.name
        out.parent.mkdir(parents=True, exist_ok=True)
        staging = Path(tempfile.mkdtemp(prefix=".resume-build-", dir=out.parent))
        starter = Path(__file__).resolve().parents[1] / "assets/starter"
        shutil.copytree(starter, staging, dirs_exist_ok=True)
        for source, relative in copy_assets:
            (staging / relative).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, staging / relative)
        write_profile(staging / "profile.js", data)
        errors, warnings = validate(data, staging, args.final)
        report(errors, warnings)
        if errors:
            return 1
        if out.exists():
            out.rmdir()  # Fails safely if another process added files in the meantime.
        staging.rename(out)
        staging = None
        print(f"已生成：{out / 'index.html'}")
        print("主页与完整阅读页共享 profile.js。外部 PDF／DOCX 内容需另行同步并核对。")
        return 0
    except (OSError, ValueError) as exc:
        print(f"生成失败：{exc}")
        return 1
    finally:
        if staging is not None:
            shutil.rmtree(staging)


if __name__ == "__main__":
    raise SystemExit(main())
