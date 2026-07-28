from __future__ import annotations

from typing import List, Optional

from .string_utils import normalize_lowercase_string_or_empty

STOP_WORDS_EN = frozenset([
    "a", "an", "the", "this", "that", "these", "those",
    "i", "me", "my", "we", "our", "you", "your", "he", "she", "it", "they", "them",
    "is", "are", "was", "were", "be", "been", "being", "have", "has", "had",
    "do", "does", "did", "will", "would", "could", "should", "can", "may", "might",
    "in", "on", "at", "to", "for", "of", "with", "by", "from", "about", "into",
    "through", "during", "before", "after", "above", "below", "between", "under", "over",
    "and", "or", "but", "if", "then", "because", "as", "while", "when", "where",
    "what", "which", "who", "how", "why",
    "yesterday", "today", "tomorrow", "earlier", "later", "recently", "ago", "just", "now",
    "thing", "things", "stuff", "something", "anything", "everything", "nothing",
    "please", "help", "find", "show", "get", "tell", "give",
])

STOP_WORDS_ZH = frozenset([
    "我", "我们", "你", "你们", "他", "她", "它", "他们", "这", "那", "这个", "那个", "这些", "那些",
    "的", "了", "着", "过", "得", "地", "吗", "呢", "吧", "啊", "呀", "嘛", "啦",
    "是", "有", "在", "被", "把", "给", "让", "用", "到", "去", "来", "做", "说", "看", "找", "想", "要", "能", "会", "可以",
    "和", "与", "或", "但", "但是", "因为", "所以", "如果", "虽然", "而", "也", "都", "就", "还", "又", "再", "才", "只",
    "之前", "以前", "之后", "以后", "刚才", "现在", "昨天", "今天", "明天", "最近",
    "东西", "事情", "事", "什么", "哪个", "哪些", "怎么", "为什么", "多少",
    "请", "帮", "帮忙", "告诉",
])

STOP_WORDS = STOP_WORDS_EN | STOP_WORDS_ZH


def is_query_stop_word_token(token: str) -> bool:
    return token in STOP_WORDS


def _is_valid_keyword(token: str) -> bool:
    if not token:
        return False
    if token.isalpha() and len(token) < 3:
        return False
    if token.isdigit():
        return False
    return True


def _tokenize(text: str, fts_tokenizer: Optional[str] = None) -> list:
    tokens = []
    normalized = normalize_lowercase_string_or_empty(text)

    segments = []
    current = []
    for ch in normalized:
        if ch.isspace() or (not ch.isalnum() and ch not in ("中", "文", "漢", "字", "か", "な", "カ", "タ", "한", "글")):
            if current:
                segments.append("".join(current))
                current = []
            if ch and not ch.isspace():
                segments.append(ch)
        else:
            current.append(ch)
    if current:
        segments.append("".join(current))

    for segment in segments:
        has_cjk = any("\u4e00" <= ch <= "\u9fff" for ch in segment)
        if has_cjk:
            chars = [ch for ch in segment if "\u4e00" <= ch <= "\u9fff"]
            if fts_tokenizer == "trigram":
                block = "".join(chars)
                if block:
                    tokens.append(block)
            else:
                tokens.extend(chars)
                for i in range(len(chars) - 1):
                    tokens.append(chars[i] + chars[i + 1])
        else:
            tokens.append(segment)

    return tokens


def extract_keywords(query: str, opts: Optional[dict] = None) -> list:
    fts_tokenizer = (opts or {}).get("ftsTokenizer")
    tokens = _tokenize(query, fts_tokenizer)
    keywords = []
    seen = set()

    for token in tokens:
        if is_query_stop_word_token(token):
            continue
        if not _is_valid_keyword(token):
            continue
        if token in seen:
            continue
        seen.add(token)
        keywords.append(token)

    return keywords


def expand_query(query: str, opts: Optional[dict] = None) -> str:
    keywords = extract_keywords(query, opts)
    if not keywords:
        return query
    return query + " " + " ".join(keywords)
