import os
import sqlite3

import pandas as pd
import streamlit as st

from logic import export_path, invalid_rows, month_rows, save_table, valid_month

VAULT_ROOT = os.environ.get("VAULT_ROOT", "vault")
VAULT_TASKS = os.path.join(VAULT_ROOT, "todolist", "active.md")

WORKOUTS = {
    "Push": ["Bench Press", "OHP", "Incline Bench", "Lateral Raise", "Tricep Pushdown"],
    "Pull":  ["Pull-ups", "Seated Row", "Lat Pulldown", "Face Pull", "Preacher Curl"],
    "Legs":  ["Squat", "Leg Press", "Leg Extension", "Leg Curl", "Calf Raise"],
    "Upper": ["Incline Bench", "Lat Pulldown", "Seated Row", "Lateral Raise", "Overhead Tricep Ext", "Preacher Curl"],
    "Lower": ["RDL", "Leg Press", "Leg Curl", "Leg Extension", "Calf Raise"],
}

def get_connection():
    return sqlite3.connect("dashboard.db")    

def init_db():
    conn = get_connection()
    conn.execute("""
    CREATE TABLE IF NOT EXISTS spending (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    amount REAL NOT NULL,
    category TEXT NOT NULL,
    note TEXT
    )
""")
    conn.commit()
    conn.close()

def init_fitness_db():
    conn = get_connection()
    conn.execute("""
    CREATE TABLE IF NOT EXISTS Fitness_Log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    workout_day TEXT NOT NULL,
    exercise TEXT NOT NULL,
    weight REAL NOT NULL,
    note TEXT
    )
""")
    conn.commit()
    conn.close()

def add_spending(date, amount, category, note):
    conn = get_connection()
    conn.execute(
    "INSERT INTO spending (date, amount, category, note) VALUES (?, ?, ?, ?)",
    (date, amount, category, note)   
    )
    conn.commit()
    conn.close()

def get_spending():
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM spending ORDER BY date DESC", conn)
    conn.close()
    return df

def add_workout(date, workout_day, exercise, weight, note):
    conn = get_connection()
    conn.execute(
        "INSERT INTO Fitness_Log (date, workout_day, exercise, weight, note) VALUES (?, ?, ?, ?, ?)",
        (date, workout_day, exercise, weight, note)
    )
    conn.commit()
    conn.close()

def get_workout():
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM Fitness_Log ORDER BY date", conn)
    conn.close()
    return df

init_db()

st.set_page_config(layout="wide")
st.title("Personal Dashboard")

tab1, tab2, tab3 =st.tabs(["SPENDING", "FITNESS", "TASKS"])

with tab1: 
    with st.form("spending_form"):
        date = st.date_input("Date")
        amount = st.number_input("Amount (₹)", min_value=0.0, step=10.0)
        category = st.selectbox("Category", ["Food & Dining", "Transport", "Shopping", "Personal Care",
    "Entertainment", "Health", "Subscriptions", "Misc"] )
        note = st.text_input("Note")
        submitted = st.form_submit_button("Add expense")

    if submitted:
        add_spending(date.isoformat(), amount, category, note)
        st.success("Saved!")

    st.header("Spending")

    df = get_spending()
  
    this_month = st.sidebar.text_input("Month (YYYY-MM)", value=pd.Timestamp.now().strftime("%Y-%m"))
    if not valid_month(this_month):
        st.error(f"Month must be YYYY-MM, e.g. 2026-10 (got {this_month!r}).")
        st.stop()
    day_filter = st.sidebar.date_input("day", value=None)

    if day_filter:
        view = df[df["date"] == day_filter.isoformat()]
    else:
        view = df

    st.dataframe(view)

    # --- month-to-date metric ---
    month_df = month_rows(df, this_month)
    total = month_df["amount"].sum()
    st.metric("Spent this month", f"₹{total:,.0f}", delta=f"₹{10000 - total:,.0f} Left")
    st.subheader("By category")

    by_category = month_df.groupby("category")["amount"].sum()
    st.bar_chart(by_category, horizontal=True)

    st.subheader("Edit / Delete")
    edited = st.data_editor(df, num_rows = "dynamic", disabled = ["id"], key = "spending editor",
                            column_config={"amount": st.column_config.NumberColumn(min_value=0)})
    if st.button("Save changes"):
        problems = invalid_rows(edited, "amount")
        if problems:
            st.error("Not saved:\n\n" + "\n\n".join(problems))
        else:
            conn = get_connection()
            save_table(conn, "spending", edited, ["date", "amount", "category", "note"])
            conn.close()
            st.success("Changes saved!")
            st.rerun()
    
    st.subheader("Month-end export")
    if st.button("Export this month to vault"):
        lines = []
        lines.append(f"## {this_month} — Spending Summary")
        lines.append("")
        lines.append(f"**Total:** ₹{total:,.0f} / ₹10,000 budget  (₹{10000 - total:,.0f} left)")
        lines.append("")
        lines.append("**By category:**")
        for cat, amt in by_category.items():
            lines.append(f"- {cat}: ₹{amt:,.0f}")
        summary = "\n".join(lines)

        spending_export = export_path(VAULT_ROOT, "dashboard", this_month)
        with open(spending_export, "w", encoding="utf-8") as f:
            f.write(summary)

        st.success(f"Exported to {spending_export}")
        st.markdown(summary)

init_fitness_db()

with tab2:
    st.header("Fitness")
    day = st.selectbox("Workout day", list(WORKOUTS.keys()))

    with st.form("fitness_form"):
        date = st.date_input("Date")
        weights = {}
        for exercise in WORKOUTS[day]:
            weights[exercise] = st.number_input(exercise, min_value=0.0, step=2.5)
        note = st.text_input("Note")
        submitted = st.form_submit_button("Save workout")

    if submitted:
        for exercise, weight in weights.items():
            add_workout(date.isoformat(), day, exercise, weight, note)
        st.success("Workout saved!")

    st.subheader("Progress")
    fdf = get_workout()
    exercise_choice = st.selectbox("Track exercise", fdf["exercise"].unique())
    ex_df = fdf[fdf["exercise"] == exercise_choice]
    st.line_chart(ex_df, x="date", y="weight")

    st.subheader("Edit / Delete")
    edited = st.data_editor(fdf, num_rows = "dynamic", disabled = ["id"], key = "Fitnesss Editor",
                            column_config={"weight": st.column_config.NumberColumn(min_value=0)})
    if st.button("Save changes", key="save fitness"):
        problems = invalid_rows(edited, "weight")
        if problems:
            st.error("Not saved:\n\n" + "\n\n".join(problems))
        else:
            conn = get_connection()
            save_table(conn, "Fitness_Log", edited, ["date", "workout_day", "exercise", "weight", "note"])
            conn.close()
            st.success("Changes saved!")
            st.rerun()

    st.subheader("Month-end export")
    if st.button("Export this month to vault", key="export_fitness"):
        month_fdf = month_rows(fdf, this_month)
        table = month_fdf.to_markdown(index=False)
        summary = f"## {this_month} — Fitness\n\n{table}\n"

        fitness_path = export_path(VAULT_ROOT, "fitness", this_month)
        with open(fitness_path, "w", encoding="utf-8") as f:
            f.write(summary)

        st.success(f"Exported to {fitness_path}")
        st.markdown(summary)


with tab3:                                 
    st.header("Tasks & Goals")
    try:
        with open(VAULT_TASKS, encoding="utf-8") as f:
            text = f.read()
        st.markdown(text)
    except FileNotFoundError:
         st.warning(f"Vault not found at `{VAULT_TASKS}` — set VAULT_ROOT or sync the vault to this machine.")

