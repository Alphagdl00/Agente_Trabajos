from __future__ import annotations

import argparse
from datetime import datetime

from config.settings import settings
from main import DEFAULT_PROFILE_PRESETS, has_run_today, run_radar

try:
    from src.telegram_alerts import send_daily_alerts
except ModuleNotFoundError:
    send_daily_alerts = None


def _parse_profiles(raw_value: str) -> list[str]:
    if not raw_value.strip():
        return ["Finance"]
    values = [item.strip() for item in raw_value.split(",") if item.strip()]
    valid = [item for item in values if item in DEFAULT_PROFILE_PRESETS]
    return valid or ["Finance"]


def main() -> None:
    parser = argparse.ArgumentParser(description="North Hound scheduled runner")
    parser.add_argument("--profiles", default=settings.SCHEDULED_PROFILES, help="Comma-separated profiles, e.g. Finance,Strategy")
    parser.add_argument("--force", action="store_true", help="Run even if North Hound already ran today")
    parser.add_argument("--full", action="store_true", help="Force a full refresh instead of auto/incremental")
    parser.add_argument("--fast", action="store_true", help="Limit companies for a faster run")
    args = parser.parse_args()

    profiles = _parse_profiles(args.profiles)
    should_skip = settings.SCHEDULE_SKIP_IF_RAN_TODAY and has_run_today() and not args.force

    print("=" * 60)
    print("NORTH HOUND SCHEDULED RUN")
    print(f"Start time: {datetime.now().isoformat()}")
    print(f"Profiles: {profiles}")
    print("=" * 60)

    if should_skip:
        print("Skipped: North Hound already ran today.")
        return

    refresh_mode = "full" if args.full else "auto"
    company_limit = 60 if args.fast else None

    result = run_radar(
        profile_name=profiles,
        save_outputs=True,
        company_limit=company_limit,
        use_parallel=True,
        refresh_mode=refresh_mode,
    )

    summary = result.get("summary", {})
    new_jobs_df = result.get("new_jobs_today")

    print("\n===== SCHEDULED RUN SUMMARY =====")
    print(f"All jobs:        {summary.get('all_jobs', 0)}")
    print(f"Filtered:        {summary.get('filtered', 0)}")
    print(f"Strong:          {summary.get('strong', 0)}")
    print(f"Priority A:      {summary.get('priority', 0)}")
    print(f"Global:          {summary.get('global', 0)}")
    print(f"New today:       {summary.get('new_today', 0)}")
    print(f"Refresh mode:    {summary.get('refresh_mode', refresh_mode)}")
    print(f"Fresh companies: {len(summary.get('fresh_companies', []))}")
    print(f"Stale companies: {len(summary.get('stale_companies', []))}")
    print("=================================\n")

    if send_daily_alerts is not None:
        send_daily_alerts(new_jobs_df, summary)
    else:
        print("Telegram alerts skipped: src.telegram_alerts no está disponible.")

    print(f"End time: {datetime.now().isoformat()}")


if __name__ == "__main__":
    main()
