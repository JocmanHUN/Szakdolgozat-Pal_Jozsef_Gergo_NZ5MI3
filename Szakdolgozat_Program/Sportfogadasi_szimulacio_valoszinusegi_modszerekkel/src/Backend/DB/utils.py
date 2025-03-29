import pytz
from dateutil import parser


def normalize_date(date_str):
    """
    Normalizálja az API-ból kapott dátumot. Ha már UTC-ben van, nem módosít rajta.
    """
    if not date_str:
        return None

    parsed_date = parser.isoparse(date_str)

    # Ha már UTC-ben van (tartalmaz "Z"-t vagy időzónát), akkor csak a formátumot egységesítjük
    if parsed_date.tzinfo is not None:
        return parsed_date.strftime("%Y-%m-%dT%H:%M:%SZ")

    # Ha nincs időzóna információ, feltételezzük, hogy helyi idő és UTC-re konvertáljuk
    return parsed_date.replace(tzinfo=pytz.utc).strftime("%Y-%m-%dT%H:%M:%SZ")