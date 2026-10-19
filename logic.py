"""Data logic for the dashboard. No Streamlit here, so every rule can be tested directly."""
import datetime
import os
import re

import pandas as pd

MONTH_RE = re.compile(r"\d{4}-(0[1-9]|1[0-2])")


def valid_month(month):
    return isinstance(month, str) and MONTH_RE.fullmatch(month) is not None


def month_rows(df, month):
    return df[df["date"].str[:7] == month]


def _valid_date(value):
    if not isinstance(value, str):
        return False
    try:
        return datetime.date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False


def invalid_rows(edited, value_col):
    """Problems that must block a save; an empty list means the edits are safe to write."""
    problems = []
    for n, row in enumerate(edited.to_dict("records"), start=1):
        if not _valid_date(row["date"]):
            problems.append(f"Row {n}: date {row['date']!r} must be YYYY-MM-DD")
        value = row[value_col]
        if pd.isna(value) or value < 0:
            problems.append(f"Row {n}: {value_col} must be a number of 0 or more")
    return problems


def save_table(conn, table, edited, columns):
    """Apply data_editor edits by id in one transaction: update kept rows, insert new ones,
    delete removed ones. Ids stay stable, and any failure rolls the whole save back."""
    with conn:
        existing = {r[0] for r in conn.execute(f"SELECT id FROM {table}")}
        kept = set()
        for row in edited.to_dict("records"):
            values = [None if pd.isna(row[c]) else row[c] for c in columns]
            if pd.isna(row["id"]):
                conn.execute(f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join('?' * len(columns))})",
                             values)
            else:
                rid = int(row["id"])
                kept.add(rid)
                conn.execute(f"UPDATE {table} SET {', '.join(c + ' = ?' for c in columns)} WHERE id = ?",
                             values + [rid])
        conn.executemany(f"DELETE FROM {table} WHERE id = ?", [(i,) for i in existing - kept])


def export_path(vault_root, kind, month):
    """One export file per month, with the folder created if missing."""
    path = os.path.join(vault_root, "finance", f"{kind}-export.md")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return path
