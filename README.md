# AI AMR Sentinel

A small Streamlit prototype for entering and exploring antimicrobial susceptibility testing (AST) records. The charts and flags are descriptive summaries, not clinical guidance or validated AI predictions.

## Run locally

1. Install Python 3.10 or newer.
2. In this folder, install the dependencies:

   ```powershell
   python -m pip install -r requirements.txt
   ```

3. Start the app:

   ```powershell
   streamlit run AI_AMR_Sentinel_app.py
   ```

Streamlit will print the local address to open in a browser. The app creates `amr_sentinel.db` beside the Python file and adds illustrative demo records when the database is empty.

## CSV format

Required columns: `sample_date`, `organism`, `antibiotic`, `susceptibility`.

Optional columns: `hospital`, `ward`, `method`, `notes`.

Use `Susceptible`, `Intermediate`, `Resistant`, or `Not tested` for susceptibility values. Dates should use `YYYY-MM-DD` format.

## Data and limitations

Use only authorized, de-identified data. The app has no login, audit trail, encrypted storage, or clinical validation. Its SQLite database is a local prototype store; protect it and make backups if you retain records. Do not use the app to diagnose infection or choose treatment.
