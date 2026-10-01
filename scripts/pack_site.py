#!/usr/bin/env python3
"""Copy an explicit public allowlist unchanged, then create a ZIP and manifest."""
import argparse
import json
import shutil
import tempfile
import zipfile
from pathlib import Path
from release_tools import file_digest, public_path, source_file, unique_paths


def main():
    parser = argparse.ArgumentParser(description="按公开文件清单打包静态网站；不修改照片、不构建、不上传。")
    parser.add_argument("--source", required=True, type=Path, help="已完成的静态源目录或构建产物")
    parser.add_argument("--files", required=True, type=Path, help="相对文件路径组成的 JSON 数组")
    parser.add_argument("--out", required=True, type=Path, help="新的或空的发布目录，必须在源目录外")
    parser.add_argument("--entry", default="index.html", help="默认 index.html；其他入口须确认平台支持")
    args = parser.parse_args()
    staging = None
    try:
        if args.source.is_symlink() or args.out.is_symlink():
            raise ValueError("源目录和输出目录不能是符号链接。")
        root, out = args.source.resolve(), args.out.resolve()
        if not root.is_dir():
            raise ValueError("源目录不存在。")
        if out == root or root in out.parents or out in root.parents:
            raise ValueError("发布目录与源目录不能相同或互相包含。")
        if out.exists() and (not out.is_dir() or any(out.iterdir())):
            raise ValueError("输出非空，已停止；请选择新的发布版本目录。")
        paths = unique_paths(json.loads(args.files.read_text(encoding="utf-8-sig")))
        entry = public_path(args.entry)
        if entry not in paths or Path(entry).suffix.lower() not in {".html", ".htm"}:
            raise ValueError("公开文件清单必须包含 HTML 入口文件。")
        sources = [(name, source_file(root, name)) for name in paths]
        args.out.parent.mkdir(parents=True, exist_ok=True)
        staging = Path(tempfile.mkdtemp(prefix=".site-release-", dir=out.parent))
        site = staging / "site"
        site.mkdir()
        manifest = {"schema_version": 1, "entry": entry, "files": []}
        for name, source in sources:
            target = site / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            size, digest = file_digest(target)
            manifest["files"].append({"path": name, "bytes": size, "sha256": digest})
        (staging / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        with zipfile.ZipFile(staging / "site.zip", "w", zipfile.ZIP_DEFLATED) as archive:
            for name in paths:
                archive.write(site / name, name)
        if out.exists():
            out.rmdir()  # Fails safely if another process filled the empty directory.
        staging.rename(out)
        staging = None
        print(f"已打包 {len(paths)} 个文件：{out / 'site'}")
        print(f"上传用 ZIP：{out / 'site.zip'}")
        print(f"私有校验清单：{out / 'manifest.json'}")
        print("文件按原字节复制；内容隐私、资源依赖和浏览器表现仍需核对。")
        return 0
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        print(f"打包失败：{exc}")
        return 1
    finally:
        if staging is not None:
            shutil.rmtree(staging)


if __name__ == "__main__":
    raise SystemExit(main())
