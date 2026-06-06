# Amount Policy

The `invoice-totaler` command uses these defaults:

- Chinese ordinary/special VAT invoices: tax-inclusive total, the `价税合计（小写）` amount.
- Railway e-ticket invoices: ticket fare, `票价`.
- Air transport itinerary invoices: total amount, `合计`, not base fare alone.
- Apple invoices: preserve USD as USD and do not convert to CNY.
- Duplicate files with the same invoice number are counted once. Structured OFD data is preferred over PDF text when both exist.
- Custom category rules only change the reporting category. Amount selection still follows the detected invoice document type, such as air itinerary total amount or railway fare.

Confidence fields:

- `high`: amount came from structured OFD fields and key fields were present.
- `medium`: amount came from PDF text heuristics and key fields were present.
- `low`: key fields are missing or no amount was found; review before relying on the row.

Common issue codes:

- `missing_invoice_no`: no invoice number was found.
- `missing_amount`: no amount was found.

When reporting results, state the policy briefly if the user is using the numbers for reimbursement, accounting, or audit.
