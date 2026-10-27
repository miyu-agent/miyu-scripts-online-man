#!/usr/bin/env python3
# Display name: Online man pages
# 显示名称：在线 man 手册
# Description: Search and read Linux man pages online (Arch Linux's man page site, man7.org as fallback), including pages for packages not installed here.
# 描述：在线搜、读 Linux man 手册（Arch Linux 的手册站，man7.org 兜底），本机没装的软件也查得到。
# Timeout: 60
# Clicall: yes
# Parameters:
# {"type": "object", "properties": {
#   "action": {"type": "string", "enum": ["search", "read"], "description": "search: find pages by name and description. read: fetch one page as plain text."},
#   "query": {"type": "string", "description": "search: keywords."},
#   "name": {"type": "string", "description": "read: page name, e.g. ls, pacman.conf, or printf(3)."},
#   "section": {"type": "string", "description": "Section, e.g. 1, 3, 5, 8, 3p. read: without it the site picks the usual one."},
#   "language": {"type": "string", "description": "Page language, e.g. en, zh_CN, ja, de; default en."},
#   "limit": {"type": "integer", "minimum": 1, "maximum": 50, "description": "search: results to list, default 10."},
#   "find": {"type": "string", "description": "read: start at the first line containing this text (an option such as --color, a heading such as EXAMPLES)."},
#   "offset": {"type": "integer", "minimum": 0, "description": "read: start at this character, to read on where the last part stopped; default 0."},
#   "max_chars": {"type": "integer", "minimum": 2000, "maximum": 60000, "description": "read: characters to return, default 12000."},
#   "format": {"type": "string", "enum": ["md", "json"], "description": "md (default) for reading; json for code, e.g. piping miyu call into jq or python."}
# }, "required": ["action"]}
"""Arch: https://man.archlinux.org/man/<name>[.<section>][.<lang>].txt is plain
text, and without a section the site redirects to the usual one. Search is the
site's HTML search page. man7.org only carries the Linux man-pages project and a
few others; it is tried when Arch has nothing.
"""

import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from html import unescape
from html.parser import HTMLParser

ARCH = "https://man.archlinux.org"
MAN7 = "https://man7.org/linux/man-pages"
UA = "miyu-online-man/0.1"
LIMIT_BYTES = 5 << 20


class NotFound(Exception):
    pass


AS_JSON = [False]   # 读参数时一认出 json 就改，出错也照它交


def fail(message):
    print(json.dumps({"ok": False, "error": message}, ensure_ascii=False) if AS_JSON[0] else f"错误：{message}")
    sys.exit(1)


def emit(text, data):
    print(json.dumps(dict({"ok": True}, **data), ensure_ascii=False) if AS_JSON[0] else text)


def get(url):
    """Body and final URL; 404 raises NotFound, other trouble ends the script."""
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.read(LIMIT_BYTES).decode("utf-8", errors="replace"), resp.geturl()
    except urllib.error.HTTPError as exc:
        if exc.code in (404, 410):
            raise NotFound(url) from None
        fail(f"{url} 回 HTTP {exc.code}")
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        fail(f"连不上 {urllib.parse.urlsplit(url).netloc}：{getattr(exc, 'reason', exc)}")


def text_arg(args, key):
    value = args.get(key)
    return value.strip() if isinstance(value, str) else ""


def int_arg(args, key, default, low, high):
    value = args.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int):
        fail(f"{key} 要是整数")
    return max(low, min(value, high))


def clean(html):
    return " ".join(unescape(re.sub(r"<[^>]+>", "", html)).split())


# ---------------------------------------------------------------- search

def search(args):
    query = text_arg(args, "query")
    if not query:
        fail("search 要给 query")
    limit = int_arg(args, "limit", 10, 1, 50)
    params = {"q": query, "lang": text_arg(args, "language") or "en"}
    if text_arg(args, "section"):
        params["section"] = text_arg(args, "section")
    url = f"{ARCH}/search?{urllib.parse.urlencode(params)}"
    try:
        html, _ = get(url)
    except NotFound:
        html = ""

    seen, results = set(), []
    # 名字里有的在前，描述里有的（apropos）在后；包名那一段不要
    for block in re.findall(r'<section class="search-results">(.*?)</section>', html, re.S):
        if "package names" in block:
            continue
        for item in re.findall(r"<li>(.*?)</li>", block, re.S):
            link = re.search(r'<a href="(/man/[^"]+)">(.*?)</a>', item, re.S)
            if not link or link.group(1) in seen:
                continue
            seen.add(link.group(1))
            package = re.search(r'from the <a href="/listing/[^"]*">([^<]+)</a>', item)
            desc = re.search(r"<dd>(.*?)</dd>", item, re.S)
            page = clean(link.group(2))
            split = re.fullmatch(r"(.+?)\((\w+)\)", page)
            results.append({"page": page, "name": split.group(1) if split else page,
                            "section": split.group(2) if split else None,
                            "package": package.group(1) if package else None,
                            "description": clean(desc.group(1)) if desc else None, "url": ARCH + link.group(1)})
    data = {"query": query, "total": len(results), "results": results[:limit]}
    if not results:
        return f"Arch 手册站没搜到「{query}」。换个词，或者直接 read 试试名字", data
    shown = []
    for r in results[:limit]:
        line = f"- {r['page']}"
        if r["package"]:
            line += f"（{r['package']}）"
        if r["description"]:
            line += f"：{r['description'][:160]}"
        shown.append(line)
    head = f"搜「{query}」，{len(results)} 条，列前 {len(shown)} 条" if len(results) > limit else f"搜「{query}」，{len(results)} 条"
    return "\n".join([head + "（括号里是 Arch 的包）：", *shown, "", "读哪一页：action=read，name 写名字，section 写括号里的数字。"]), data


# ---------------------------------------------------------------- read

class Man7Text(HTMLParser):
    """man7 pages put each section's body in <pre> under an <h2> heading."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.heading = None
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag == "pre":
            self.depth += 1
        elif tag == "h2":
            self.heading = []

    def handle_endtag(self, tag):
        if tag == "pre" and self.depth:
            self.depth -= 1
            self.parts.append("\n")
        elif tag == "h2" and self.heading is not None:
            title = " ".join("".join(self.heading).split())
            title = re.sub(r"\s*top$", "", title)
            if title:
                self.parts.append(f"\n{title}\n")
            self.heading = None

    def handle_data(self, data):
        if self.heading is not None:
            self.heading.append(data)
        elif self.depth:
            self.parts.append(data)


class MandocText(HTMLParser):
    """Arch's HTML pages (mandoc) to text in the usual man layout: headings at
    the margin, body indented, option lists as term + indented description."""

    BLOCKS = {"p", "dd", "dt", "h1", "h2", "pre", "li", "tr", "div"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.inside = 0  # within <div class="manual-text">
        self.depth = 0
        self.pre = 0
        self.tag = None
        self.buf = []
        self.lines = []

    def flush(self):
        text = "".join(self.buf)
        self.buf = []
        if self.pre:
            self.lines += ["       " + line for line in text.strip("\n").split("\n")] + [""]
            return
        text = " ".join(text.split())
        if not text:
            return
        indent = {"h1": "", "h2": "   ", "dd": "              "}.get(self.tag, "       ")
        self.lines.append(indent + text)
        if self.tag not in ("dt",):
            self.lines.append("")

    def handle_starttag(self, tag, attrs):
        if not self.inside:
            if tag == "div" and ("class", "manual-text") in attrs:
                self.inside, self.depth = 1, 1
            return
        if tag == "div":
            self.depth += 1
        if tag in self.BLOCKS:
            self.flush()
            self.tag = tag
            if tag == "pre":
                self.pre += 1
        elif tag == "br":
            self.buf.append("\n" if self.pre else " ")

    def handle_endtag(self, tag):
        if not self.inside:
            return
        if tag in self.BLOCKS:
            self.flush()
            if tag == "pre":
                self.pre = max(0, self.pre - 1)
        if tag == "div":
            self.depth -= 1
            if not self.depth:
                self.inside = 0

    def handle_data(self, data):
        if self.inside:
            self.buf.append(data)

    def text(self):
        self.flush()
        return re.sub(r"\n{3,}", "\n\n", "\n".join(self.lines)).strip("\n") + "\n"


def from_arch(name, section, language):
    """English: the site's .txt. Other languages: the .txt export drops every
    non-ASCII letter, so read the HTML page instead."""
    stem = urllib.parse.quote(".".join([name] + ([section] if section else [])))
    if language == "en":
        return get(f"{ARCH}/man/{stem}.txt")
    html, final = get(f"{ARCH}/man/{stem}.{urllib.parse.quote(language)}")
    parser = MandocText()
    parser.feed(html)
    return parser.text(), final


def from_man7(name, section):
    tried = [section] if section else ["1", "8", "5", "7", "2", "3"]
    for sec in tried:
        url = f"{MAN7}/man{sec[0]}/{urllib.parse.quote(name)}.{sec}.html"
        try:
            html, final = get(url)
        except NotFound:
            continue
        parser = Man7Text()
        parser.feed(html)
        text = "".join(parser.parts).strip()
        # man7 tacks a colophon on the end of each page
        text = re.split(r"\n\s*COLOPHON\s*\n", text)[0].rstrip()
        text = re.sub(r"\n{3,}", "\n\n", text)
        if text:
            return text + "\n", final
    raise NotFound(name)


def read(args):
    name = text_arg(args, "name")
    if not name:
        fail("read 要给 name")
    section = text_arg(args, "section")
    match = re.fullmatch(r"(.+?)\s*\((\w+)\)", name)  # printf(3)
    if match:
        name, section = match.group(1), section or match.group(2)
    if not re.fullmatch(r"[\w.@:+-]+", name) or (section and not re.fullmatch(r"\w+", section)):
        fail(f"名字或者章节写法不对：{name} {section}".strip())
    language = text_arg(args, "language") or "en"
    offset = int_arg(args, "offset", 0, 0, 10**9)
    max_chars = int_arg(args, "max_chars", 12000, 2000, 60000)

    try:
        text, source = from_arch(name, section, language)
    except NotFound:
        try:
            text, source = from_man7(name, section)
        except NotFound:
            where = f"第 {section} 节" if section else "任何一节"
            lang = "" if language == "en" else f"（{language}）"
            fail(f"找不到 {name}{lang} 在{where}的手册页。拼写对吗？可以先 action=search 搜一下"
                 + ("，或者去掉 language 读英文版" if language != "en" else ""))

    total = len(text)
    find = args.get("find")
    if isinstance(find, str) and find.strip():
        hit = text.find(find.strip(), offset)
        if hit == -1:
            fail(f"{name} 的手册里没有「{find.strip()}」" + (f"（从第 {offset} 字往后找）" if offset else ""))
        offset = text.rfind("\n", 0, hit) + 1
    if offset >= total:
        fail(f"offset {offset} 超过了全文长度 {total}")
    piece = text[offset:offset + max_chars]
    end = offset + len(piece)
    head = f"来源：{source}"
    fallback = language != "en" and f".{language}" not in source
    if fallback:
        head += f"（没有 {language} 版，这是英文版）"
    if offset or end < total:
        head += f"（全文 {total} 字，这是第 {offset}–{end} 字）"
    out = [head, "", piece.rstrip("\n")]
    if end < total:
        out += ["", f"……没完，接着读：offset={end}"]
    data = {"name": name, "section": section or None, "language": "en" if fallback else language,
            "language_fallback": fallback, "source": source, "total_chars": total, "offset": offset, "end": end,
            "next_offset": end if end < total else None, "text": piece}
    return "\n".join(out), data


def known_params():
    """开头 Parameters 里写的参数名：不认识的参数直接报错，免得写错的名字被悄悄当成没给。"""
    lines, inside = [], False
    with open(__file__, encoding="utf-8") as f:
        for line in f:
            if not line.startswith("#"):
                break
            if line.startswith("# Parameters:"):
                inside = True
            elif inside:
                lines.append(line[1:])
    return set(json.loads("".join(lines)).get("properties", {}))


def reject_unknown(args):
    unknown = sorted(set(args) - known_params())
    if unknown:
        fail(f"不认识的参数：{'、'.join(unknown)}。能用的：{'、'.join(sorted(known_params()))}")


def main():
    try:
        args = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        fail(f"参数不是 JSON：{exc}")
    if not isinstance(args, dict):
        fail("参数要是一个 JSON 对象")
    AS_JSON[0] = args.get("format") == "json"
    reject_unknown(args)
    if args.get("format") not in (None, "md", "json"):
        fail(f"format 只认 md、json，不认 {args['format']}")
    action = args.get("action")
    if action == "search":
        emit(*search(args))
    elif action == "read":
        emit(*read(args))
    else:
        fail("action 要是 search 或 read")


if __name__ == "__main__":
    main()
