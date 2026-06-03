# Amount Policy

The `invoice-totaler` command uses these defaults:

- Chinese ordinary/special VAT invoices: tax-inclusive total, the `价税合计（小写）` amount.
- Railway e-ticket invoices: ticket fare, `票价`.
- Air transport itinerary invoices: total amount, `合计`, not base fare alone.
- Apple invoices: preserve USD as USD and do not convert to CNY.
- Duplicate files with the same invoice number are counted once. Structured OFD data is preferred over PDF text when both exist.

When reporting results, state the policy briefly if the user is using the numbers for reimbursement, accounting, or audit.
