import sqlite3
from pathlib import Path
from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st

APP_DIR = Path(__file__).parent
DB_PATH = APP_DIR / "amr_sentinel.db"

st.set_page_config(
    page_title="AI AMR Sentinel",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------- Storage ----------
def connect_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS isolates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sample_date TEXT NOT NULL,
            hospital TEXT,
            ward TEXT,
            organism TEXT NOT NULL,
            antibiotic TEXT NOT NULL,
            susceptibility TEXT NOT NULL,
            method TEXT,
            notes TEXT
        )
    """)
    conn.commit()
    return conn

conn = connect_db()

def load_data():
    return pd.read_sql_query(
        "SELECT id, sample_date, hospital, ward, organism, antibiotic, susceptibility, method, notes FROM isolates ORDER BY sample_date DESC, id DESC",
        conn,
    )

def seed_demo_data():
    count = conn.execute("SELECT COUNT(*) FROM isolates").fetchone()[0]
    if count:
        return
    demo = [
        ("2026-01-05", "Demo Hospital", "ICU", "Escherichia coli", "Ciprofloxacin", "Resistant", "Disk diffusion", "Illustrative demo record"),
        ("2026-01-08", "Demo Hospital", "Medicine", "Escherichia coli", "Ceftriaxone", "Susceptible", "Disk diffusion", "Illustrative demo record"),
        ("2026-01-12", "Demo Hospital", "ICU", "Klebsiella pneumoniae", "Meropenem", "Resistant", "MIC", "Illustrative demo record"),
        ("2026-01-16", "Demo Hospital", "Surgery", "Staphylococcus aureus", "Cefoxitin", "Resistant", "Disk diffusion", "Illustrative demo record"),
        ("2026-01-20", "Demo Hospital", "Medicine", "Pseudomonas aeruginosa", "Piperacillin-tazobactam", "Susceptible", "MIC", "Illustrative demo record"),
        ("2026-02-02", "Demo Hospital", "ICU", "Klebsiella pneumoniae", "Ceftriaxone", "Resistant", "Disk diffusion", "Illustrative demo record"),
        ("2026-02-06", "Demo Hospital", "Medicine", "Escherichia coli", "Ciprofloxacin", "Intermediate", "Disk diffusion", "Illustrative demo record"),
        ("2026-02-11", "Demo Hospital", "ICU", "Acinetobacter baumannii", "Meropenem", "Resistant", "MIC", "Illustrative demo record"),
        ("2026-02-18", "Demo Hospital", "Surgery", "Staphylococcus aureus", "Vancomycin", "Susceptible", "MIC", "Illustrative demo record"),
        ("2026-03-01", "Demo Hospital", "ICU", "Pseudomonas aeruginosa", "Ciprofloxacin", "Resistant", "Disk diffusion", "Illustrative demo record"),
        ("2026-03-05", "Demo Hospital", "Medicine", "Escherichia coli", "Ceftriaxone", "Intermediate", "Disk diffusion", "Illustrative demo record"),
        ("2026-03-10", "Demo Hospital", "ICU", "Klebsiella pneumoniae", "Meropenem", "Resistant", "MIC", "Illustrative demo record"),
    ]
    conn.executemany(
        """INSERT INTO isolates
        (sample_date, hospital, ward, organism, antibiotic, susceptibility, method, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        demo,
    )
    conn.commit()

seed_demo_data()

ORGANISMS = [
    "Escherichia coli", "Klebsiella pneumoniae", "Staphylococcus aureus",
    "Pseudomonas aeruginosa", "Acinetobacter baumannii", "Enterococcus faecium",
    "Enterococcus faecalis", "Enterobacter cloacae", "Other / not listed",
]
ANTIBIOTICS = [
    "Amoxicillin-clavulanate", "Ceftriaxone", "Ceftazidime", "Cefepime",
    "Meropenem", "Imipenem", "Ciprofloxacin", "Levofloxacin",
    "Piperacillin-tazobactam", "Gentamicin", "Amikacin", "Vancomycin",
    "Linezolid", "Cefoxitin", "Other / not listed",
]
RESULTS = ["Susceptible", "Intermediate", "Resistant", "Not tested"]

# ---------- Sidebar ----------
st.sidebar.title("🧬 AMR Sentinel")
st.sidebar.caption("Antimicrobial resistance surveillance prototype")
page = st.sidebar.radio(
    "Navigation",
    ["Dashboard", "Add laboratory record", "Explore records", "Import / Export", "About & limitations"],
)
st.sidebar.divider()
st.sidebar.caption("Demo data are illustrative. Replace them with authorized, de-identified laboratory data.")

df = load_data()
if not df.empty:
    df["sample_date"] = pd.to_datetime(df["sample_date"], errors="coerce")

# ---------- Helpers ----------
def metric_resistance(frame):
    tested = frame[frame["susceptibility"].isin(["Susceptible", "Intermediate", "Resistant"])]
    if tested.empty:
        return 0.0
    return 100 * (tested["susceptibility"] == "Resistant").sum() / len(tested)

def clean_for_csv(frame):
    return frame.drop(columns=["id"], errors="ignore").copy()

# ---------- Dashboard ----------
if page == "Dashboard":
    st.title("AI AMR Sentinel")
    st.write("Antimicrobial resistance surveillance and trend exploration")
    st.info(
        "Prototype notice: this app summarizes entered laboratory results. "
        "Its pattern flags are descriptive, not a validated AI model or clinical decision support."
    )

    total = len(df)
    tested = int(df["susceptibility"].isin(["Susceptible", "Intermediate", "Resistant"]).sum()) if total else 0
    resistant = int((df["susceptibility"] == "Resistant").sum()) if total else 0
    resistance_pct = metric_resistance(df) if total else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Records", f"{total:,}")
    c2.metric("Tested results", f"{tested:,}")
    c3.metric("Resistant results", f"{resistant:,}")
    c4.metric("Resistant among tested", f"{resistance_pct:.1f}%")
    st.caption("This share combines test records across antibiotics; it is not an isolate- or patient-level prevalence estimate.")

    if df.empty:
        st.warning("No records available yet. Add a record or import a CSV.")
    else:
        left, right = st.columns(2)
        with left:
            st.subheader("Resistance by organism and antibiotic")
            summary = (
                df[df["susceptibility"].isin(["Susceptible", "Intermediate", "Resistant"])]
                .groupby(["organism", "antibiotic"])
                .agg(tested=("susceptibility", "size"),
                     resistant=("susceptibility", lambda s: (s == "Resistant").sum()))
                .reset_index()
            )
            summary["Resistance (%)"] = (100 * summary["resistant"] / summary["tested"]).round(1)
            if not summary.empty:
                summary["Organism / antibiotic"] = summary["organism"] + " / " + summary["antibiotic"]
                fig = px.bar(summary.sort_values("Resistance (%)", ascending=False),
                             x="Organism / antibiotic", y="Resistance (%)", hover_data=["tested", "resistant"],
                             range_y=[0, 100], labels={"Organism / antibiotic": "Organism / antibiotic"},
                             title="Resistant results / tested results by organism and antibiotic")
                fig.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.caption("No tested results to chart.")
        with right:
            st.subheader("Susceptibility result distribution")
            counts = df["susceptibility"].value_counts().rename_axis("Result").reset_index(name="Count")
            fig = px.pie(counts, names="Result", values="Count", hole=0.45)
            st.plotly_chart(fig, use_container_width=True)

        st.subheader("Recent records")
        st.dataframe(df.head(8), use_container_width=True, hide_index=True)

        st.subheader("Pattern flags (descriptive only)")
        st.caption("Flags are generated from this dataset only; small samples can be misleading.")
        flags = []
        tested_df = df[df["susceptibility"].isin(["Susceptible", "Intermediate", "Resistant"])]
        if tested_df.empty:
            st.write("No tested records available.")
        else:
            by_pair = tested_df.groupby(["organism", "antibiotic"]).agg(
                tested=("susceptibility", "size"),
                resistant=("susceptibility", lambda s: int((s == "Resistant").sum())),
            ).reset_index()
            by_pair["resistance_pct"] = 100 * by_pair["resistant"] / by_pair["tested"]
            for _, row in by_pair.iterrows():
                if row["tested"] >= 3 and row["resistance_pct"] >= 50:
                    flags.append(
                        f"{row['organism']} — {row['antibiotic']}: "
                        f"{row['resistance_pct']:.0f}% resistant ({int(row['resistant'])}/{int(row['tested'])})."
                    )
            if flags:
                for flag in flags:
                    st.warning(flag)
            else:
                st.success("No organism–antibiotic pair met the prototype flag rule (at least 3 tested records and ≥50% resistant). This does not establish absence of a clinical concern.")

# ---------- Add record ----------
elif page == "Add laboratory record":
    st.title("Add laboratory record")
    st.write("Enter de-identified antimicrobial susceptibility testing (AST) data.")
    with st.form("add_record", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            sample_date = st.date_input("Sample date", value=date.today())
            hospital = st.text_input("Facility / hospital label", value="Demo Hospital")
            ward = st.text_input("Ward / unit", placeholder="e.g., ICU, Medicine")
            organism_choice = st.selectbox("Organism", ORGANISMS)
            organism = (
                st.text_input("Specify organism")
                if organism_choice == "Other / not listed"
                else organism_choice
            )
        with col2:
            antibiotic_choice = st.selectbox("Antibiotic tested", ANTIBIOTICS)
            antibiotic = (
                st.text_input("Specify antibiotic")
                if antibiotic_choice == "Other / not listed"
                else antibiotic_choice
            )
            susceptibility = st.selectbox("AST result", RESULTS)
            method = st.selectbox("Testing method", ["Disk diffusion", "MIC", "Automated system", "Other / not specified"])
            notes = st.text_area("Notes (optional)", placeholder="Do not enter patient names or identifiers.")
        submitted = st.form_submit_button("Save record", type="primary")
        if submitted:
            if not organism.strip() or not antibiotic.strip():
                st.error("Enter an organism and antibiotic before saving the record.")
            else:
                conn.execute(
                    """INSERT INTO isolates
                    (sample_date, hospital, ward, organism, antibiotic, susceptibility, method, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (sample_date.isoformat(), hospital.strip(), ward.strip(), organism.strip(), antibiotic.strip(),
                     susceptibility, method, notes.strip()),
                )
                conn.commit()
                st.success("Record saved to the local SQLite database.")
                st.rerun()

# ---------- Explore ----------
elif page == "Explore records":
    st.title("Explore records")
    if df.empty:
        st.info("No records to display.")
    else:
        f1, f2, f3 = st.columns(3)
        organism_options = ["All"] + sorted(df["organism"].dropna().unique().tolist())
        antibiotic_options = ["All"] + sorted(df["antibiotic"].dropna().unique().tolist())
        result_options = ["All"] + sorted(df["susceptibility"].dropna().unique().tolist())
        selected_org = f1.selectbox("Filter organism", organism_options)
        selected_ab = f2.selectbox("Filter antibiotic", antibiotic_options)
        selected_result = f3.selectbox("Filter result", result_options)

        filtered = df.copy()
        if selected_org != "All":
            filtered = filtered[filtered["organism"] == selected_org]
        if selected_ab != "All":
            filtered = filtered[filtered["antibiotic"] == selected_ab]
        if selected_result != "All":
            filtered = filtered[filtered["susceptibility"] == selected_result]

        st.caption(f"{len(filtered)} matching record(s)")
        st.dataframe(filtered, use_container_width=True, hide_index=True)
        st.download_button(
            "Download filtered records as CSV",
            data=clean_for_csv(filtered).to_csv(index=False).encode("utf-8"),
            file_name="amr_sentinel_filtered_records.csv",
            mime="text/csv",
        )

        st.subheader("Delete a record")
        record_ids = filtered["id"].astype(int).tolist()
        if record_ids:
            delete_id = st.selectbox("Select record ID", record_ids)
            confirm = st.checkbox("I understand this permanently deletes the selected local record.")
            if st.button("Delete selected record", disabled=not confirm):
                conn.execute("DELETE FROM isolates WHERE id = ?", (int(delete_id),))
                conn.commit()
                st.success(f"Deleted record ID {delete_id}.")
                st.rerun()

# ---------- Import / Export ----------
elif page == "Import / Export":
    st.title("Import / Export data")
    st.markdown("""
Upload a CSV with these column names (case-insensitive):  
`sample_date, organism, antibiotic, susceptibility`  
Optional columns: `hospital, ward, method, notes`.
""")
    uploaded = st.file_uploader("Choose a CSV file", type=["csv"])
    if uploaded is not None:
        try:
            incoming = pd.read_csv(uploaded)
            incoming.columns = [str(c).strip().lower() for c in incoming.columns]
            required = {"sample_date", "organism", "antibiotic", "susceptibility"}
            missing = required - set(incoming.columns)
            if missing:
                st.error("Missing required columns: " + ", ".join(sorted(missing)))
            else:
                for col in ["hospital", "ward", "method", "notes"]:
                    if col not in incoming.columns:
                        incoming[col] = ""
                for col in ["organism", "antibiotic", "susceptibility", "hospital", "ward", "method", "notes"]:
                    incoming[col] = incoming[col].fillna("").astype(str).str.strip()
                incoming["sample_date"] = pd.to_datetime(incoming["sample_date"], errors="coerce").dt.strftime("%Y-%m-%d")
                incoming["susceptibility"] = incoming["susceptibility"].str.title()
                valid_results = {"Susceptible", "Intermediate", "Resistant", "Not Tested"}
                invalid = sorted(set(incoming["susceptibility"].dropna()) - valid_results)
                missing_values = [
                    col for col in ["organism", "antibiotic", "susceptibility"]
                    if incoming[col].eq("").any()
                ]
                st.write(f"Rows detected: {len(incoming)}")
                if incoming.empty:
                    st.error("The CSV contains no records to import.")
                elif missing_values:
                    st.error("Missing values in required fields: " + ", ".join(missing_values))
                elif invalid:
                    st.error("Unrecognized susceptibility values: " + ", ".join(invalid))
                elif incoming["sample_date"].isna().any():
                    st.error("Some sample_date values could not be parsed. Use YYYY-MM-DD dates.")
                else:
                    st.dataframe(incoming.head(10), use_container_width=True, hide_index=True)
                    if st.button("Import these records", type="primary"):
                        rows = []
                        for _, r in incoming.iterrows():
                            rows.append((
                                str(r["sample_date"]), str(r["hospital"]), str(r["ward"]),
                                str(r["organism"]), str(r["antibiotic"]), str(r["susceptibility"]),
                                str(r["method"]), str(r["notes"])
                            ))
                        conn.executemany(
                            """INSERT INTO isolates
                            (sample_date, hospital, ward, organism, antibiotic, susceptibility, method, notes)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                            rows,
                        )
                        conn.commit()
                        st.success(f"Imported {len(rows)} records.")
                        st.rerun()
        except Exception as exc:
            st.error(f"Could not read this CSV: {exc}")

    st.divider()
    st.subheader("Export all records")
    all_df = load_data()
    st.download_button(
        "Download all records as CSV",
        data=clean_for_csv(all_df).to_csv(index=False).encode("utf-8"),
        file_name="amr_sentinel_all_records.csv",
        mime="text/csv",
    )
    st.caption(f"Database location: {DB_PATH.name} (local file beside app.py)")

# ---------- About ----------
else:
    st.title("About AI AMR Sentinel")
    st.markdown("""
**Purpose:** a student-project prototype for recording and exploring antimicrobial susceptibility results.

**Included in this version**
- Interactive dashboard and descriptive charts
- Local SQLite storage
- Manual record entry, filtering, CSV import and export
- Transparent rule-based pattern flags

**Important limitations**
- The “AI” label describes the intended project concept; this code does not call a trained AI model.
- Charts and flags describe only the data entered. They are not validated predictions and may be misleading with small or biased samples.
- Do not use this app to diagnose infection, select treatment, or replace a clinical microbiology laboratory, infectious-disease specialist, or local antibiogram.
- Interpret AST results using the current standards and procedures adopted by your laboratory (for example, current CLSI or EUCAST guidance).
- Use only authorized, de-identified data. Do not upload patient names, identifiers, or confidential hospital data to a demo.
- Before real-world deployment, add authentication, role-based access, audit logs, secure backups, input validation, privacy review, and formal clinical validation.
""")
    st.subheader("Suggested next upgrades")
    st.markdown("""
1. User login and roles for laboratory staff and administrators.
2. Standardized organism / antimicrobial naming and AST breakpoints linked to an approved, maintained source.
3. Time-series monitoring with minimum sample-size safeguards.
4. A validated model trained on a documented dataset, with performance evaluation and human oversight.
5. Deployment to a secure server with encrypted storage and backups.
""")

conn.close()
