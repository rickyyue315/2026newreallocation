def is_hd_to_hk_restricted(source_site: str, dest_site: str) -> bool:
    source_upper = source_site.upper()
    dest_upper = dest_site.upper()
    return source_upper.startswith("HD") and any(
        dest_upper.startswith(prefix) for prefix in ("HA", "HB", "HC")
    )
