from __future__ import annotations

import argparse
import importlib.util
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from . import __version__
from .core import load_category_rules, parse_invoice_file, scan_invoice_files, summarize_invoices
from .report import write_csv, write_json, write_xlsx


def extract_archive(path: Path) -> tempfile.TemporaryDirectory[str]:
    tempdir = tempfile.TemporaryDirectory(prefix="invoice-totaler-")
    target = Path(tempdir.name)
    if path.suffix.lower() == ".zip":
        shutil.unpack_archive(str(path), str(target))
        return tempdir
    command = None
    if shutil.which("7zz"):
        command = ["7zz", "x", "-y", f"-o{target}", str(path)]
    elif shutil.which("7z"):
        command = ["7z", "x", "-y", f"-o{target}", str(path)]
    elif shutil.which("bsdtar"):
        command = ["bsdtar", "-xf", str(path), "-C", str(target)]
    if command is None:
        tempdir.cleanup()
        raise RuntimeError("解压 .7z 需要安装 7zz、7z 或 bsdtar。也可以先手动解压后传入目录。")
    subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return tempdir


def source_root(input_path: Path) -> tuple[Path, tempfile.TemporaryDirectory[str] | None]:
    if input_path.is_dir() or input_path.suffix.lower() in {".pdf", ".ofd"}:
        return input_path, None
    tempdir = extract_archive(input_path)
    return Path(tempdir.name), tempdir


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="invoice-totaler",
        description="统计 PDF/OFD 发票金额，按分类去重汇总，并导出 JSON/CSV/XLSX。",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("input", help="发票目录、单个 PDF/OFD，或 .zip/.7z 压缩包")
    parser.add_argument("-o", "--output", default="invoice-summary.xlsx", help="输出文件路径")
    parser.add_argument("--format", choices=["xlsx", "csv", "json"], default="xlsx", help="输出格式")
    parser.add_argument("--strict", action="store_true", help="发现低置信度或缺字段发票时返回退出码 2")
    parser.add_argument("--category-rules", help="自定义分类规则 JSON 文件路径")
    return parser


def doctor() -> int:
    checks = [
        ("pypdf", importlib.util.find_spec("pypdf") is not None, "PDF 解析依赖"),
        ("7zz/7z/bsdtar", any(shutil.which(name) for name in ["7zz", "7z", "bsdtar"]), ".7z 解压工具"),
    ]
    print(f"invoice-totaler {__version__}")
    for name, ok, description in checks:
        status = "ok" if ok else "missing"
        print(f"{status:7} {name} - {description}")
    if not checks[0][1]:
        print("缺少 pypdf 时无法解析 PDF；请重新安装 invoice-amount-tool。")
        return 1
    if not checks[1][1]:
        print("未找到 .7z 解压工具；仍可处理目录、单个 PDF/OFD 和 .zip。")
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] == "doctor":
        return doctor()
    parser = build_parser()
    args = parser.parse_args(argv)
    input_path = Path(args.input).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()
    if not input_path.exists():
        parser.error(f"input not found: {input_path}")
    category_rules = []
    if args.category_rules:
        rules_path = Path(args.category_rules).expanduser().resolve()
        if not rules_path.exists():
            parser.error(f"category rules not found: {rules_path}")
        try:
            category_rules = load_category_rules(rules_path)
        except ValueError as exc:
            parser.error(str(exc))
    tempdir = None
    try:
        root, tempdir = source_root(input_path)
        files = scan_invoice_files(root)
        invoices = []
        for file in files:
            parsed = parse_invoice_file(file, category_rules)
            if parsed is not None:
                invoices.append(parsed)
        summary = summarize_invoices(invoices, all_file_count=len(files))
        if args.format == "xlsx":
            write_xlsx(summary, output_path)
        elif args.format == "csv":
            write_csv(summary, output_path)
        else:
            write_json(summary, output_path)
    finally:
        if tempdir is not None:
            tempdir.cleanup()
    cny_total = sum(total.amount for total in summary.totals.values() if total.currency == "CNY")
    usd_total = sum(total.amount for total in summary.totals.values() if total.currency == "USD")
    print(f"Parsed {summary.all_file_count} files -> {summary.unique_count} unique invoices")
    print(f"CNY total: {cny_total:,.2f}")
    if usd_total:
        print(f"USD total: {usd_total:,.2f}")
    if summary.problem_rows:
        print(f"Problems: {len(summary.problem_rows)} invoice(s) need review")
    print(f"Wrote: {output_path}")
    return 2 if args.strict and summary.problem_rows else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
