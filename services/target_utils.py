import math
import re
import unicodedata
from typing import Any


def parse_target_series(target_value: Any) -> tuple[bool, float, list[float], str]:
    if target_value is None:
        return False, 0.0, [], ""

    raw = str(target_value).strip()
    raw = unicodedata.normalize("NFKC", raw)

    raw_clean = raw.replace(",", "")

    try:
        parsed = float(raw_clean)
        if parsed <= 0:
            return False, 0.0, [], raw_clean
        return True, parsed, [parsed], raw_clean
    except (ValueError, TypeError):
        pass

    parts = re.split(r"[,\s]+", raw_clean)
    numeric_parts = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        try:
            numeric_parts.append(float(p))
        except (ValueError, TypeError):
            pass

    if not numeric_parts:
        return False, 0.0, [], raw_clean

    return True, sum(numeric_parts), numeric_parts, raw_clean
