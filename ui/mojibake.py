import unicodedata


def fix_mojibake(text: str) -> str:
    if not text:
        return text
    try:
        text.encode("latin-1")
        return text
    except UnicodeEncodeError:
        pass
    try:
        return text.encode("latin-1").decode("utf-8")
    except (UnicodeDecodeError, UnicodeEncodeError):
        pass
    try:
        return text.encode("latin-1").decode("gbk")
    except (UnicodeDecodeError, UnicodeEncodeError):
        pass
    return unicodedata.normalize("NFKC", text)
