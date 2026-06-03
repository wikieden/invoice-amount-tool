import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from invoice_amount_tool.cli import main


def make_railway_ofd(path: Path, invoice_no: str = "26949134178000969211") -> None:
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
    <xbrl xmlns:rai="http://xbrl.mof.gov.cn/taxonomy/2021-11-30/rai">
      <rai:ElectronicInvoiceRailwayETicketNumber>{invoice_no}</rai:ElectronicInvoiceRailwayETicketNumber>
      <rai:DateOfIssue>2026-05-24</rai:DateOfIssue>
      <rai:TrainNumber>G256</rai:TrainNumber>
      <rai:DepartureStation>厦门北</rai:DepartureStation>
      <rai:DestinationStation>杭州东</rai:DestinationStation>
      <rai:TravelDate>2026-03-18</rai:TravelDate>
      <rai:Fare>493.00</rai:Fare>
      <rai:TaxAmount>40.71</rai:TaxAmount>
    </xbrl>
    """
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("Doc_0/Attachs/rai_issuer.xml", xml)


class CliInputTests(unittest.TestCase):
    def test_cli_accepts_single_invoice_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            invoice = Path(tmp) / "ticket.ofd"
            output = Path(tmp) / "summary.json"
            make_railway_ofd(invoice)

            exit_code = main([str(invoice), "--format", "json", "-o", str(output)])

            self.assertEqual(exit_code, 0)
            data = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(data["unique_count"], 1)
            self.assertEqual(data["rows"][0]["amount"], 493.0)

    def test_cli_accepts_invoice_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "invoices"
            root.mkdir()
            make_railway_ofd(root / "ticket-a.ofd", "26949134178000969211")
            make_railway_ofd(root / "ticket-b.ofd", "26949134178000969212")
            output = Path(tmp) / "summary.json"

            exit_code = main([str(root), "--format", "json", "-o", str(output)])

            self.assertEqual(exit_code, 0)
            data = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(data["unique_count"], 2)
            self.assertEqual(data["totals"][0]["amount"], 986.0)

    def test_strict_mode_returns_nonzero_when_invoice_has_issues(self):
        with tempfile.TemporaryDirectory() as tmp:
            invoice = Path(tmp) / "empty.ofd"
            output = Path(tmp) / "summary.json"
            with zipfile.ZipFile(invoice, "w") as zf:
                zf.writestr("OFD.xml", "<ofd></ofd>")

            exit_code = main([str(invoice), "--format", "json", "-o", str(output), "--strict"])

            self.assertEqual(exit_code, 2)
            data = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(data["problem_count"], 1)
            self.assertIn("missing_amount", data["problem_rows"][0]["issues"])

    def test_doctor_command_runs_dependency_checks(self):
        exit_code = main(["doctor"])

        self.assertEqual(exit_code, 0)


if __name__ == "__main__":
    unittest.main()
