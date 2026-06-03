from __future__ import annotations

import csv
import html
import zipfile
from pathlib import Path

from .core import InvoiceSummary


DETAIL_HEADERS = [
    "分类",
    "开票日期",
    "行程日期",
    "发票号码",
    "币种",
    "金额",
    "税额",
    "销售方",
    "购买方",
    "行程/项目",
    "来源文件",
    "备注",
]


def write_json(summary: InvoiceSummary, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(summary.to_json(), encoding="utf-8")


def write_csv(summary: InvoiceSummary, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["分类汇总"])
        writer.writerow(["分类", "币种", "张数", "金额合计"])
        for total in sorted(summary.totals.values(), key=lambda item: (item.currency, item.category)):
            writer.writerow([total.category, total.currency, total.count, f"{total.amount:.2f}"])
        writer.writerow([])
        writer.writerow(["明细"])
        writer.writerow(DETAIL_HEADERS)
        for row in summary.rows:
            writer.writerow(
                [
                    row.category,
                    row.issue_date or "",
                    row.travel_date or "",
                    row.invoice_no or "",
                    row.currency,
                    f"{float(row.amount or 0):.2f}",
                    "" if row.tax is None else f"{float(row.tax):.2f}",
                    row.seller or "",
                    row.buyer or "",
                    row.route_or_item or "",
                    row.source_file,
                    row.note,
                ]
            )


def _col_name(index: int) -> str:
    name = ""
    index += 1
    while index:
        index, remainder = divmod(index - 1, 26)
        name = chr(65 + remainder) + name
    return name


def _cell_xml(row_index: int, col_index: int, value: object) -> str:
    ref = f"{_col_name(col_index)}{row_index + 1}"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return f'<c r="{ref}"><v>{value}</v></c>'
    escaped = html.escape("" if value is None else str(value))
    return f'<c r="{ref}" t="inlineStr"><is><t>{escaped}</t></is></c>'


def _sheet_xml(rows: list[list[object]]) -> str:
    sheet_rows = []
    for row_index, row in enumerate(rows):
        cells = "".join(_cell_xml(row_index, col_index, value) for col_index, value in enumerate(row))
        sheet_rows.append(f'<row r="{row_index + 1}">{cells}</row>')
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        "<sheetData>"
        + "".join(sheet_rows)
        + "</sheetData></worksheet>"
    )


def write_xlsx(summary: InvoiceSummary, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    overview_rows: list[list[object]] = [
        ["发票金额分类统计"],
        [],
        ["原始 PDF/OFD 文件数", summary.all_file_count],
        ["去重后发票数", summary.unique_count],
        [
            "人民币合计",
            round(sum(total.amount for total in summary.totals.values() if total.currency == "CNY"), 2),
        ],
        [
            "美元合计",
            round(sum(total.amount for total in summary.totals.values() if total.currency == "USD"), 2),
        ],
        ["统计口径", "中文发票取含税总额；火车票取票价；机票取合计；外币不做汇率换算"],
        [],
        ["分类", "币种", "张数", "金额合计"],
    ]
    for total in sorted(summary.totals.values(), key=lambda item: (item.currency, item.category)):
        overview_rows.append([total.category, total.currency, total.count, total.amount])

    detail_rows: list[list[object]] = [DETAIL_HEADERS]
    for row in summary.rows:
        detail_rows.append(
            [
                row.category,
                row.issue_date or "",
                row.travel_date or "",
                row.invoice_no or "",
                row.currency,
                float(row.amount or 0),
                "" if row.tax is None else float(row.tax),
                row.seller or "",
                row.buyer or "",
                row.route_or_item or "",
                row.source_file,
                row.note,
            ]
        )

    duplicate_rows: list[list[object]] = [["去重键/发票号", "重复文件数", "重复文件列表"]]
    for key, files in sorted(summary.duplicates.items()):
        duplicate_rows.append([key, len(files), "\n".join(files)])

    sheets = [("总览", overview_rows), ("明细", detail_rows), ("重复文件", duplicate_rows)]
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            + "".join(
                f'<Override PartName="/xl/worksheets/sheet{index}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
                for index in range(1, len(sheets) + 1)
            )
            + "</Types>",
        )
        zf.writestr(
            "_rels/.rels",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            "</Relationships>",
        )
        zf.writestr(
            "xl/workbook.xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>'
            + "".join(
                f'<sheet name="{html.escape(name)}" sheetId="{index}" r:id="rId{index}"/>'
                for index, (name, _) in enumerate(sheets, start=1)
            )
            + "</sheets></workbook>",
        )
        zf.writestr(
            "xl/_rels/workbook.xml.rels",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            + "".join(
                f'<Relationship Id="rId{index}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{index}.xml"/>'
                for index in range(1, len(sheets) + 1)
            )
            + "</Relationships>",
        )
        for index, (_, rows) in enumerate(sheets, start=1):
            zf.writestr(f"xl/worksheets/sheet{index}.xml", _sheet_xml(rows))
