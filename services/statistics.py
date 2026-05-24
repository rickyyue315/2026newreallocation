from collections import defaultdict


def compute_transfer_statistics(recommendations: list) -> dict:
    if not recommendations:
        return {
            "total_recommendations": 0,
            "total_transfer_qty": 0,
            "unique_articles": 0,
            "unique_oms": 0,
            "article_stats": {},
            "om_stats": {},
            "source_type_stats": {},
            "dest_type_stats": {},
        }

    total_qty = sum(r.get("Transfer Qty", 0) for r in recommendations)
    articles = set(r.get("Article", "") for r in recommendations)
    transfer_oms = set(r.get("Transfer OM", "") for r in recommendations)

    article_stats = defaultdict(lambda: {"total_qty": 0, "count": 0, "om_count": 0})
    article_oms: dict[str, set] = defaultdict(set)

    for r in recommendations:
        article = r.get("Article", "")
        qty = r.get("Transfer Qty", 0)
        om = r.get("Transfer OM", "")

        article_stats[article]["total_qty"] += qty
        article_stats[article]["count"] += 1
        article_oms[article].add(om)

    for article in article_stats:
        article_stats[article]["om_count"] = len(article_oms.get(article, set()))

    om_stats = defaultdict(lambda: {
        "total_qty": 0, "transfer_qty": 0, "receive_qty": 0, "count": 0, "article_count": 0,
    })
    om_articles: dict[str, set] = defaultdict(set)

    for r in recommendations:
        transfer_om = r.get("Transfer OM", "")
        receive_om = r.get("Receive OM", "")
        qty = r.get("Transfer Qty", 0)
        article = r.get("Article", "")

        om_stats[transfer_om]["total_qty"] += qty
        om_stats[transfer_om]["transfer_qty"] += qty
        om_stats[transfer_om]["count"] += 1
        om_articles[transfer_om].add(article)

        om_stats[receive_om]["total_qty"] += qty
        om_stats[receive_om]["receive_qty"] += qty
        om_articles[receive_om].add(article)

    for om in om_stats:
        om_stats[om]["article_count"] = len(om_articles.get(om, set()))

    source_type_stats = defaultdict(lambda: {"count": 0, "qty": 0})
    dest_type_stats = defaultdict(lambda: {"count": 0, "qty": 0})

    for r in recommendations:
        source_type = r.get("Source Type", "Unknown")
        dest_type = r.get("Destination Type", "Unknown")
        qty = r.get("Transfer Qty", 0)

        source_type_stats[source_type]["count"] += 1
        source_type_stats[source_type]["qty"] += qty

        dest_type_stats[dest_type]["count"] += 1
        dest_type_stats[dest_type]["qty"] += qty

    return {
        "total_recommendations": len(recommendations),
        "total_transfer_qty": total_qty,
        "unique_articles": len(articles),
        "unique_oms": len(transfer_oms),
        "article_stats": dict(article_stats),
        "om_stats": dict(om_stats),
        "source_type_stats": dict(source_type_stats),
        "dest_type_stats": dict(dest_type_stats),
    }
