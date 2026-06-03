"""
Parse ADCB-format bank statement CSV files into a standard list of transactions.

The ADCB CSV format has 6 header rows (bank name, account holder, etc.),
then a blank row, then a header row with columns:
    Transaction Date, Value Date, Description, Reference No,
    Debit (AED), Credit (AED), Balance (AED)

Returns a list of dicts:
    {date, description, amount, kind, account, raw_balance}
"""

import csv
from datetime import datetime
from pathlib import Path
from typing import Literal


def parse_adcb_csv(filepath: str | Path,
                   account_kind: Literal["savings", "credit_card"]) -> list[dict]:
    """Parse one ADCB statement CSV. Returns list of transaction dicts."""
    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"CSV not found: {filepath}")

    transactions = []
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)

    # Find the header row dynamically (handles variations in header lines)
    header_idx = None
    for i, row in enumerate(rows):
        if row and row[0] == "Transaction Date":
            header_idx = i
            break

    if header_idx is None:
        raise ValueError(f"Could not find 'Transaction Date' header in {filepath}")

    headers = rows[header_idx]
    col_idx = {h: i for i, h in enumerate(headers)}

    for row in rows[header_idx + 1:]:
        if not row or len(row) < len(headers):
            continue
        try:
            date_str = row[col_idx["Transaction Date"]]
            description = row[col_idx["Description"]].strip()
            debit_str = row[col_idx["Debit (AED)"]].strip()
            credit_str = row[col_idx["Credit (AED)"]].strip()
            balance_str = row[col_idx["Balance (AED)"]].strip()

            # ADCB format dates: DD/MM/YYYY
            date_iso = datetime.strptime(date_str, "%d/%m/%Y").date().isoformat()

            if debit_str:
                amount = float(debit_str.replace(",", ""))
                kind = "debit"
            elif credit_str:
                amount = float(credit_str.replace(",", ""))
                kind = "credit"
            else:
                continue

            transactions.append({
                "date": date_iso,
                "description": description,
                "amount": amount,
                "kind": kind,
                "account": account_kind,
                "balance": float(balance_str.replace(",", "")) if balance_str else None,
            })
        except (KeyError, ValueError, IndexError):
            # Skip malformed rows silently — real-world CSVs are messy
            continue

    return transactions


def load_all_transactions(csv_paths: list[str]) -> list[dict]:
    """Load transactions from multiple CSV files, inferring account type from filename."""
    all_tx = []
    for path in csv_paths:
        p = Path(path)
        if "CreditCard" in p.name or "Credit_Card" in p.name:
            kind = "credit_card"
        else:
            kind = "savings"
        all_tx.extend(parse_adcb_csv(p, kind))
    # Sort by date
    all_tx.sort(key=lambda t: t["date"])
    return all_tx
