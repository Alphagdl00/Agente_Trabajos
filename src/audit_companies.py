from pathlib import Path
import pandas as pd

from ats_detector import summarize_url

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "config"
OUTPUT_DIR = BASE_DIR / "output"


def main():
    companies_file = CONFIG_DIR / "companies.csv"
    output_file = OUTPUT_DIR / "companies_audit.xlsx"

    df = pd.read_csv(companies_file)

    audit_rows = []

    for _, row in df.iterrows():
        company = row.get("company", "")
        ats_csv = row.get("ats", "")
        career_url = row.get("career_url", "")

        summary = summarize_url(career_url)

        audit_rows.append({
            "company": company,
            "ats_in_csv": ats_csv,
            "ats_detected": summary["ats_detected"],
            "career_url": career_url,
            "domain": summary["domain"],
            "is_workday_board": summary["is_workday_board"],
            "match": str(ats_csv).strip().lower() == str(summary["ats_detected"]).strip().lower(),
        })

    audit_df = pd.DataFrame(audit_rows)
    OUTPUT_DIR.mkdir(exist_ok=True)
    audit_df.to_excel(output_file, index=False)

    print(f"Archivo generado: {output_file}")
    print(f"Empresas auditadas: {len(audit_df)}")

    mismatches = audit_df[audit_df["match"] == False]
    print(f"Empresas con ATS inconsistente: {len(mismatches)}")


if __name__ == "__main__":
    main()