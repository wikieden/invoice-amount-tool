import sys
import tempfile
import types
import unittest
import zipfile
from pathlib import Path

from invoice_amount_tool.core import Invoice, parse_invoice_text, parse_ofd_file, parse_pdf_file, summarize_invoices


class InvoiceParsingTests(unittest.TestCase):
    def test_regular_invoice_uses_tax_inclusive_total(self):
        text = (
            "电子发票（普通发票） 发票号码：26332000004305034306 "
            "¥479.21 ¥4.79 价税合计（大写） 肆佰捌拾肆圆整 （小写） ¥ 484.00 "
            "*餐饮服务*餐费"
        )

        invoice = parse_invoice_text(Path("23日聚餐479.21.pdf"), text)

        self.assertEqual(invoice.category, "餐饮")
        self.assertEqual(invoice.invoice_no, "26332000004305034306")
        self.assertEqual(invoice.currency, "CNY")
        self.assertEqual(invoice.amount, 484.0)
        self.assertEqual(invoice.amount_source, "pdf_tax_inclusive_total")
        self.assertEqual(invoice.confidence, "medium")
        self.assertEqual(invoice.issues, ())

    def test_air_ticket_uses_total_amount_not_fare(self):
        text = (
            "电子发票（航空运输电子客票行程单） 发票号码:26948731111036166786 "
            "CNY 733.94 CNY 18.35 9% CNY 67.71 CNY 50.00 CNY 0.00 CNY 870.00"
        )

        invoice = parse_invoice_text(Path("机票/电子行程单_26948731111036166786.pdf"), text)

        self.assertEqual(invoice.category, "机票")
        self.assertEqual(invoice.amount, 870.0)
        self.assertEqual(invoice.amount_source, "pdf_air_total")

    def test_ofd_railway_ticket_reads_structured_fare(self):
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <xbrl xmlns:rai="http://xbrl.mof.gov.cn/taxonomy/2021-11-30/rai">
          <rai:ElectronicInvoiceRailwayETicketNumber>26949134178000969211</rai:ElectronicInvoiceRailwayETicketNumber>
          <rai:DateOfIssue>2026-05-24</rai:DateOfIssue>
          <rai:TrainNumber>G256</rai:TrainNumber>
          <rai:DepartureStation>厦门北</rai:DepartureStation>
          <rai:DestinationStation>杭州东</rai:DestinationStation>
          <rai:TravelDate>2026-03-18</rai:TravelDate>
          <rai:Fare>493.00</rai:Fare>
          <rai:TaxAmount>40.71</rai:TaxAmount>
        </xbrl>
        """
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ticket.ofd"
            with zipfile.ZipFile(path, "w") as zf:
                zf.writestr("Doc_0/Attachs/rai_issuer.xml", xml)

            invoice = parse_ofd_file(path)

        self.assertEqual(invoice.category, "火车票")
        self.assertEqual(invoice.invoice_no, "26949134178000969211")
        self.assertEqual(invoice.amount, 493.0)
        self.assertEqual(invoice.route_or_item, "G256 厦门北 - 杭州东")
        self.assertEqual(invoice.amount_source, "structured_ofd")
        self.assertEqual(invoice.confidence, "high")

    def test_unrecognized_invoice_records_low_confidence_issues(self):
        invoice = parse_invoice_text(Path("unknown.pdf"), "not an invoice")

        self.assertEqual(invoice.confidence, "low")
        self.assertEqual(invoice.amount_source, "none")
        self.assertIn("missing_invoice_no", invoice.issues)
        self.assertIn("missing_amount", invoice.issues)

    def test_pdf_text_extraction_failure_becomes_problem_row(self):
        class BrokenPage:
            def extract_text(self):
                raise RuntimeError("broken font")

        class FakePdfReader:
            def __init__(self, path):
                self.pages = [BrokenPage()]

        original = sys.modules.get("pypdf")
        sys.modules["pypdf"] = types.SimpleNamespace(PdfReader=FakePdfReader)
        try:
            invoice = parse_pdf_file(Path("broken.pdf"))
        finally:
            if original is None:
                sys.modules.pop("pypdf", None)
            else:
                sys.modules["pypdf"] = original

        self.assertEqual(invoice.confidence, "low")
        self.assertEqual(invoice.amount_source, "none")
        self.assertIn("pdf_text_extraction_failed", invoice.issues)
        self.assertIn("missing_amount", invoice.issues)

    def test_summary_deduplicates_by_invoice_number(self):
        invoices = [
            Invoice(
                key="26332000004002532021",
                source_file="a.pdf",
                file_type="pdf",
                category="房租",
                invoice_no="26332000004002532021",
                issue_date="2026-05-14",
                travel_date=None,
                amount=3655.0,
                currency="CNY",
                tax=None,
                seller=None,
                buyer=None,
                route_or_item=None,
                note="PDF文本",
                amount_source="pdf_tax_inclusive_total",
                confidence="medium",
                issues=(),
            ),
            Invoice(
                key="26332000004002532021",
                source_file="b.pdf",
                file_type="pdf",
                category="房租",
                invoice_no="26332000004002532021",
                issue_date="2026-05-14",
                travel_date=None,
                amount=3655.0,
                currency="CNY",
                tax=None,
                seller=None,
                buyer=None,
                route_or_item=None,
                note="PDF文本",
                amount_source="pdf_tax_inclusive_total",
                confidence="medium",
                issues=(),
            ),
        ]

        summary = summarize_invoices(invoices)

        self.assertEqual(summary.unique_count, 1)
        self.assertEqual(summary.totals[("房租", "CNY")].amount, 3655.0)
        self.assertEqual(summary.duplicates["26332000004002532021"], ["a.pdf", "b.pdf"])

    def test_summary_exposes_problem_rows(self):
        invoice = parse_invoice_text(Path("unknown.pdf"), "not an invoice")

        summary = summarize_invoices([invoice])

        self.assertEqual(len(summary.problem_rows), 1)
        self.assertEqual(summary.problem_rows[0].source_file, "unknown.pdf")
        self.assertEqual(summary.to_dict()["problem_count"], 1)


if __name__ == "__main__":
    unittest.main()
