#!/usr/bin/env python3
"""Check starter data and linked local resources without executing JavaScript."""
import argparse
from pathlib import Path
from profile_tools import read_profile, report, validate


def main():
    parser = argparse.ArgumentParser(description="检查简历底稿的数据和本地资源，不代替事实核对及浏览器验收。")
    parser.add_argument("directory", type=Path)
    parser.add_argument("--final", action="store_true", help="拒绝草稿标记和未替换示例")
    args = parser.parse_args()
    try:
        root = args.directory.resolve()
        errors = [f"缺少文件：{name}" for name in ("index.html", "resume.html", "styles.css", "app.js", "profile.js") if not (root / name).is_file()]
        if errors:
            report(errors, [])
            return 1
        data = read_profile(root / "profile.js")
        errors, warnings = validate(data, root, args.final)
        report(errors, warnings)
        if errors:
            return 1
        print("检查通过：字段与本地资源可用。请继续检查真实内容、排版、导航及实际下载。")
        return 0
    except (OSError, ValueError) as exc:
        print(f"检查失败：{exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
