"""Daily accessibility history built from report counts.

Used by the per-website history endpoint and the system-wide dashboard. Both walk
reports oldest to newest, keep the latest counts known for every page, and emit one
aggregate point per day on which any page was scanned. Carrying the latest counts
forward keeps a day's total correct when only some pages were rescanned that day.
"""

CATEGORIES = ('violations', 'incomplete', 'passes')
SUBKEYS = ('total', 'critical', 'serious', 'moderate', 'minor')


def empty_counts() -> dict:
    return {category: {subkey: 0 for subkey in SUBKEYS} for category in CATEGORIES}


def sum_counts(per_site: dict) -> dict:
    """Sum ``report_counts`` dicts (one per page) into a single counts dict."""
    total = empty_counts()
    for counts in per_site.values():
        if not counts:
            continue
        for category in CATEGORIES:
            category_counts = counts.get(category)
            if not category_counts:
                continue
            for subkey in SUBKEYS:
                total[category][subkey] += category_counts.get(subkey, 0) or 0
    return total


def daily_history(rows) -> list[dict]:
    """``rows`` are ``(site_id, timestamp, report_counts)`` tuples ordered oldest to
    newest. Returns ``[{'date': 'YYYY-MM-DD', 'report_counts': {...}}, ...]``."""
    items = []
    latest_per_site = {}
    current_day = None
    for site_id, timestamp, report_counts in rows:
        if not timestamp:
            continue
        day = timestamp.strftime("%Y-%m-%d")
        if current_day is not None and day != current_day:
            items.append({'date': current_day, 'report_counts': sum_counts(latest_per_site)})
        latest_per_site[site_id] = report_counts
        current_day = day
    if current_day is not None:
        items.append({'date': current_day, 'report_counts': sum_counts(latest_per_site)})
    return items
