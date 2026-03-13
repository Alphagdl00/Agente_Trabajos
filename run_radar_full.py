from __future__ import annotations

from datetime import datetime

from main import DEFAULT_PROFILE_PRESETS, run_radar

try:
    from src.telegram_alerts import send_daily_alerts
except ModuleNotFoundError:
    send_daily_alerts = None


def main():
    keywords = DEFAULT_PROFILE_PRESETS["Finance"]

    print("=" * 60)
    print("RUNNING FULL DAILY RADAR")
    print(f"Start time: {datetime.now().isoformat()}")
    print("=" * 60)

    result = run_radar(
        keywords=keywords,
        save_outputs=True,
        company_limit=None,
        use_parallel=True,
    )

    summary = result.get("summary", {})
    new_jobs_df = result.get("new_jobs_today")

    print("\n===== FULL RADAR SUMMARY =====")
    print(f"All jobs:       {summary.get('all_jobs', 0)}")
    print(f"Filtered:       {summary.get('filtered', 0)}")
    print(f"Strong:         {summary.get('strong', 0)}")
    print(f"Priority A:     {summary.get('priority', 0)}")
    print(f"Global:         {summary.get('global', 0)}")
    print(f"New today:      {summary.get('new_today', 0)}")
    print("==============================\n")

    if send_daily_alerts is not None:
        send_daily_alerts(new_jobs_df, summary)
    else:
        print("Telegram alerts skipped: src.telegram_alerts no está disponible.")

    print(f"End time: {datetime.now().isoformat()}")


if __name__ == "__main__":
    main()
