from __future__ import annotations

import json
import re
import zipfile
from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable
from xml.etree import ElementTree as ET


@dataclass(frozen=True)
class Invoice:
    key: str
    source_file: str
    file_type: str
    category: str
    invoice_no: str | None
    issue_date: str | None
    travel_date: str | None
    amount: float | None
    currency: str
    tax: float | None
    seller: str | None
    buyer: str | None
    route_or_item: str | None
    note: str
    amount_source: str = "none"
    confidence: str = "low"
    issues: tuple[str, ...] = ()


@dataclass(frozen=True)
class CategoryRule:
    category: str
    path_contains: tuple[str, ...] = ()
    text_contains: tuple[str, ...] = ()

    def matches(self, path: Path, text: str) -> bool:
        path_text = str(path)
        path_ok = not self.path_contains or any(token in path_text for token in self.path_contains)
        text_ok = not self.text_contains or any(token in text for token in self.text_contains)
        return path_ok and text_ok


@dataclass(frozen=True)
class CategoryTotal:
    category: str
    currency: str
    count: int
    amount: float


@dataclass(frozen=True)
class InvoiceSummary:
    all_file_count: int
    parsed_count: int
    unique_count: int
    rows: list[Invoice]
    totals: dict[tuple[str, str], CategoryTotal]
    duplicates: dict[str, list[str]]

    @property
    def problem_rows(self) -> list[Invoice]:
        return [row for row in self.rows if row.issues or row.confidence == "low"]

    def to_dict(self) -> dict[str, Any]:
        return {
            "all_file_count": self.all_file_count,
            "parsed_count": self.parsed_count,
            "unique_count": self.unique_count,
            "problem_count": len(self.problem_rows),
            "rows": [asdict(row) for row in self.rows],
            "problem_rows": [asdict(row) for row in self.problem_rows],
            "totals": [
                asdict(total)
                for _, total in sorted(self.totals.items(), key=lambda item: (item[0][1], item[0][0]))
            ],
            "duplicates": self.duplicates,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def decimal_or_none(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return float(Decimal(value.replace(",", "").strip()))
    except InvalidOperation:
        return None


def _local_name(elem: ET.Element) -> str:
    return elem.tag.rsplit("}", 1)[-1]


def _first_text_by_local(root: ET.Element, names: Iterable[str]) -> str | None:
    wanted = set(names)
    for elem in root.iter():
        if _local_name(elem) in wanted and elem.text and elem.text.strip():
            return elem.text.strip()
    return None


def _custom_data(root: ET.Element) -> dict[str, str]:
    fields: dict[str, str] = {}
    for elem in root.iter():
        if _local_name(elem) == "CustomData":
            name = elem.attrib.get("Name")
            if name and elem.text:
                fields[name] = elem.text.strip()
    return fields


def _text_codes(xml_bytes: bytes) -> str:
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return ""
    return " ".join(
        elem.text.strip()
        for elem in root.iter()
        if _local_name(elem) == "TextCode" and elem.text and elem.text.strip()
    )


def _strings_from_rule(value: object, field_name: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return tuple(value)
    raise ValueError(f"category rule field {field_name!r} must be a string or list of strings")


def load_category_rules(path: Path) -> list[CategoryRule]:
    data = json.loads(path.read_text(encoding="utf-8"))
    raw_rules = data.get("rules") if isinstance(data, dict) else data
    if not isinstance(raw_rules, list):
        raise ValueError("category rules must be a list or an object with a 'rules' list")
    rules: list[CategoryRule] = []
    for index, raw_rule in enumerate(raw_rules, start=1):
        if not isinstance(raw_rule, dict):
            raise ValueError(f"category rule #{index} must be an object")
        category = raw_rule.get("category")
        if not isinstance(category, str) or not category.strip():
            raise ValueError(f"category rule #{index} requires a non-empty category")
        rule = CategoryRule(
            category=category.strip(),
            path_contains=_strings_from_rule(raw_rule.get("path_contains"), "path_contains"),
            text_contains=_strings_from_rule(raw_rule.get("text_contains"), "text_contains"),
        )
        if not rule.path_contains and not rule.text_contains:
            raise ValueError(f"category rule #{index} requires path_contains or text_contains")
        rules.append(rule)
    return rules


def custom_category_for(path: Path, text: str, category_rules: Iterable[CategoryRule] = ()) -> str | None:
    for rule in category_rules:
        if rule.matches(path, text):
            return rule.category
    return None


def category_for(path: Path, text: str, category_rules: Iterable[CategoryRule] = ()) -> str:
    custom_category = custom_category_for(path, text, category_rules)
    if custom_category:
        return custom_category
    path_text = str(path)
    if "/房租/" in path_text or "租金" in path.name or "房租" in path.name:
        return "房租"
    if "/火车票/" in path_text or "铁路电子客票" in text:
        return "火车票"
    if "/机票/" in path_text or "航空运输电子客票" in text:
        return "机票"
    if "Apple" in path.name or "Apple Store" in text:
        return "Apple礼品卡"
    if "餐饮" in text or "聚餐" in path.name:
        return "餐饮"
    return "其他"


def invoice_no_from_text(text: str, path: Path) -> str | None:
    dense = re.sub(r"(?<=\d)\s+(?=\d)", "", text)
    match = re.search(r"发票号码[:：\s]*([0-9]{20})", dense)
    if match:
        return match.group(1)
    match = re.search(r"Invoice Number\s*\|?\s*([A-Z0-9-]{6,})", text, re.I)
    if match:
        return match.group(1)
    match = re.search(r"(26\d{18})", path.stem)
    if match:
        return match.group(1)
    match = re.search(r"(26\d{18})", dense)
    if match:
        return match.group(1)
    return None


def issue_date_from_text(text: str) -> str | None:
    match = re.search(r"开票日期[:：\s]*(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日", text)
    if not match:
        match = re.search(r"(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日", text)
    if match:
        year, month, day = match.groups()
        return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
    match = re.search(r"Invoice Date\s*\|?\s*([A-Za-z]+ \d{1,2}, \d{4})", text)
    if match:
        return match.group(1)
    return None


def normalize_date(value: str | None) -> str | None:
    if not value:
        return None
    match = re.match(r"(\d{4})[-年](\d{1,2})[-月](\d{1,2})", value)
    if match:
        year, month, day = match.groups()
        return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
    return value


def amount_from_text(text: str, category: str) -> tuple[float | None, str, str]:
    if category == "Apple礼品卡":
        match = re.search(r"Total\s*\$([0-9,]+\.\d{2})", text)
        return (decimal_or_none(match.group(1)) if match else None, "USD", "pdf_apple_total" if match else "none")
    if category == "机票":
        cny_values = [
            amount for amount in (decimal_or_none(value) for value in re.findall(r"CNY\s*([0-9,]+\.\d{2})", text))
            if amount is not None
        ]
        return (cny_values[-1] if cny_values else None, "CNY", "pdf_air_total" if cny_values else "none")
    if category == "火车票":
        match = re.search(r"票价\s*[:：]?\s*￥\s*([0-9,]+\.\d{2})", text)
        if not match:
            match = re.search(r"票价\s*[:：]?.{0,20}?￥\s*\|?\s*([0-9,]+\.\d{2})", text)
        if not match:
            match = re.search(r"￥\s*\|?\s*([0-9,]+\.\d{2})", text)
        return (decimal_or_none(match.group(1)) if match else None, "CNY", "pdf_railway_fare" if match else "none")
    money_values = [
        amount
        for amount in (
            decimal_or_none(re.sub(r"\s+", "", value))
            for value in re.findall(r"[¥￥]\s*([0-9\s,]+\.\s*\d{2})", text)
        )
        if amount is not None
    ]
    return (max(money_values) if money_values else None, "CNY", "pdf_tax_inclusive_total" if money_values else "none")


def invoice_issues(invoice_no: str | None, amount: float | None, extra_issues: Iterable[str] = ()) -> tuple[str, ...]:
    issues: list[str] = list(extra_issues)
    if not invoice_no:
        issues.append("missing_invoice_no")
    if amount is None:
        issues.append("missing_amount")
    return tuple(issues)


def confidence_for(amount_source: str, issues: tuple[str, ...]) -> str:
    if issues:
        return "low"
    if amount_source == "structured_ofd":
        return "high"
    return "medium"


def parse_invoice_text(
    path: Path,
    text: str,
    extra_issues: Iterable[str] = (),
    category_rules: Iterable[CategoryRule] = (),
) -> Invoice:
    text = clean_text(text)
    built_in_category = category_for(path, text)
    category = custom_category_for(path, text, category_rules) or built_in_category
    invoice_no = invoice_no_from_text(text, path)
    amount, currency, amount_source = amount_from_text(text, built_in_category)
    issue_date = issue_date_from_text(text)
    key = invoice_no or f"{category}:{path.stem}:{amount}:{currency}"
    issues = invoice_issues(invoice_no, amount, extra_issues)
    return Invoice(
        key=key,
        source_file=str(path),
        file_type=path.suffix.lower().lstrip(".") or "text",
        category=category,
        invoice_no=invoice_no,
        issue_date=issue_date,
        travel_date=None,
        amount=amount,
        currency=currency,
        tax=None,
        seller=None,
        buyer=None,
        route_or_item=None,
        note="PDF文本",
        amount_source=amount_source,
        confidence=confidence_for(amount_source, issues),
        issues=issues,
    )


def _amount_from_ofd_fields(fields: dict[str, str]) -> float | None:
    amount = decimal_or_none(fields.get("amount"))
    if amount is not None:
        return amount
    if fields.get("合计金额") and fields.get("合计税额"):
        return float(Decimal(fields["合计金额"]) + Decimal(fields["合计税额"]))
    return None


def parse_ofd_file(path: Path, category_rules: Iterable[CategoryRule] = ()) -> Invoice:
    fields: dict[str, str] = {}
    text_parts: list[str] = []
    with zipfile.ZipFile(path) as zf:
        for name in zf.namelist():
            if not name.lower().endswith(".xml"):
                continue
            data = zf.read(name)
            if name.endswith("OFD.xml"):
                try:
                    fields.update(_custom_data(ET.fromstring(data)))
                except ET.ParseError:
                    pass
            if "/Attachs/" in name:
                try:
                    root = ET.fromstring(data)
                except ET.ParseError:
                    continue
                is_air = _first_text_by_local(
                    root,
                    ["ElectronicInvoiceAirTransportReceiptNumber", "NumberOfAirTransportElectronicTicketItinerary"],
                )
                is_rail = _first_text_by_local(root, ["ElectronicInvoiceRailwayETicketNumber"])
                if is_air:
                    amount_value = _first_text_by_local(root, ["TotalAmount"])
                elif is_rail:
                    amount_value = _first_text_by_local(root, ["Fare"])
                else:
                    amount_value = _first_text_by_local(root, ["TaxInclusiveTotalAmount", "TotalAmount"])
                extracted = {
                    "invoice_no": _first_text_by_local(
                        root,
                        [
                            "ElectronicInvoiceRailwayETicketNumber",
                            "ElectronicInvoiceAirTransportReceiptNumber",
                            "ElectronicInvoiceAirTransportETicketNumber",
                            "NumberOfAirTransportElectronicTicketItinerary",
                        ],
                    ),
                    "issue_date": _first_text_by_local(root, ["DateOfIssue", "IssueDate"]),
                    "travel_date": _first_text_by_local(root, ["TravelDate", "CarrierDate", "FlightDate"]),
                    "train_no": _first_text_by_local(root, ["TrainNumber"]),
                    "flight_no": _first_text_by_local(root, ["Flight", "FlightNumber"]),
                    "departure": _first_text_by_local(root, ["DepartureStation", "DepartureAirport"]),
                    "destination": _first_text_by_local(root, ["DestinationStation", "DestinationAirport"]),
                    "seller": _first_text_by_local(root, ["IssueParty", "NameOfSeller"]),
                    "buyer": _first_text_by_local(root, ["NameOfPurchaser"]),
                    "amount": amount_value,
                    "tax": _first_text_by_local(root, ["TaxAmount", "VatTaxAmount"]),
                }
                fields.update({key: value for key, value in extracted.items() if value})
            if name.endswith("Content.xml") or name.endswith("OFD.xml"):
                text_parts.append(_text_codes(data))
    text = clean_text(" ".join(text_parts))
    rule_text = clean_text(" ".join([text, *fields.values()]))
    custom_category = custom_category_for(path, rule_text, category_rules)
    category = custom_category or category_for(path, text)
    if not custom_category and fields.get("train_no"):
        category = "火车票"
    elif not custom_category and (fields.get("flight_no") or "AirTransport" in "".join(fields.keys())):
        category = "机票"
    route = " - ".join(part for part in [fields.get("departure"), fields.get("destination")] if part) or None
    if fields.get("train_no"):
        route = f"{fields['train_no']} {route or ''}".strip()
    if fields.get("flight_no"):
        route = f"{fields['flight_no']} {route or ''}".strip()
    amount = _amount_from_ofd_fields(fields)
    invoice_no = fields.get("invoice_no") or invoice_no_from_text(text, path)
    key = invoice_no or f"{category}:{path.stem}:{amount}:CNY"
    amount_source = "structured_ofd" if amount is not None and fields else "none"
    issues = invoice_issues(invoice_no, amount)
    return Invoice(
        key=key,
        source_file=str(path),
        file_type="ofd",
        category=category,
        invoice_no=invoice_no,
        issue_date=normalize_date(fields.get("issue_date")),
        travel_date=normalize_date(fields.get("travel_date")),
        amount=amount,
        currency="CNY",
        tax=decimal_or_none(fields.get("tax")),
        seller=fields.get("seller"),
        buyer=fields.get("buyer"),
        route_or_item=route,
        note="结构化OFD" if fields else "OFD文本",
        amount_source=amount_source,
        confidence=confidence_for(amount_source, issues),
        issues=issues,
    )


def parse_pdf_file(path: Path, category_rules: Iterable[CategoryRule] = ()) -> Invoice:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError("PDF parsing requires the pypdf package. Install with `pip install pypdf`.") from exc
    try:
        reader = PdfReader(str(path))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        return parse_invoice_text(path, text, category_rules=category_rules)
    except Exception:
        return parse_invoice_text(path, "", extra_issues=("pdf_text_extraction_failed",), category_rules=category_rules)


def parse_invoice_file(path: Path, category_rules: Iterable[CategoryRule] = ()) -> Invoice | None:
    suffix = path.suffix.lower()
    if suffix == ".ofd":
        return parse_ofd_file(path, category_rules)
    if suffix == ".pdf":
        return parse_pdf_file(path, category_rules)
    return None


def _prefer(existing: Invoice, candidate: Invoice) -> Invoice:
    def score(invoice: Invoice) -> tuple[int, int, int]:
        return (
            3 if invoice.note == "结构化OFD" else 1,
            1 if invoice.amount is not None else 0,
            -len(invoice.source_file),
        )

    return candidate if score(candidate) > score(existing) else existing


def summarize_invoices(invoices: Iterable[Invoice], all_file_count: int | None = None) -> InvoiceSummary:
    parsed_rows = list(invoices)
    deduped: dict[str, Invoice] = {}
    duplicates: dict[str, list[str]] = {}
    for invoice in parsed_rows:
        if invoice.key in deduped:
            duplicates.setdefault(invoice.key, [deduped[invoice.key].source_file]).append(invoice.source_file)
            deduped[invoice.key] = _prefer(deduped[invoice.key], invoice)
        else:
            deduped[invoice.key] = invoice
    rows = sorted(deduped.values(), key=lambda item: (item.category, item.issue_date or "", item.invoice_no or ""))
    totals_acc: dict[tuple[str, str], list[float]] = {}
    for row in rows:
        key = (row.category, row.currency)
        current = totals_acc.setdefault(key, [0, 0.0])
        current[0] += 1
        current[1] += float(row.amount or 0)
    totals = {
        key: CategoryTotal(category=key[0], currency=key[1], count=int(value[0]), amount=round(value[1], 2))
        for key, value in totals_acc.items()
    }
    return InvoiceSummary(
        all_file_count=all_file_count if all_file_count is not None else len(parsed_rows),
        parsed_count=len(parsed_rows),
        unique_count=len(rows),
        rows=rows,
        totals=totals,
        duplicates=duplicates,
    )


def scan_invoice_files(root: Path) -> list[Path]:
    if root.is_file():
        return [root] if root.suffix.lower() in {".pdf", ".ofd"} else []
    return sorted(path for path in root.rglob("*") if path.suffix.lower() in {".pdf", ".ofd"})
