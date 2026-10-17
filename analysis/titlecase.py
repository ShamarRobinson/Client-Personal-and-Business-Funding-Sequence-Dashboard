"""Title case for every title and subheading (body text stays in sentence case).

Rules (Chicago-style headline case):
- Capitalize the first and last word, and the first word after a colon, semicolon, dash or "?".
- Lowercase articles, coordinating conjunctions and short prepositions in the middle of a title.
- Capitalize each part of a hyphenated word ("Self-Published", "Year-1").
- Leave words that already carry capitals or start with a number or symbol untouched
  (KDP, IngramSpark, ISBNs, $16.99, 2025, A/B, KENP).
"""
import re

SMALL = {"a", "an", "the", "and", "but", "or", "nor", "for", "so", "yet", "as", "at", "by", "in", "of",
         "off", "on", "per", "to", "up", "via", "vs", "vs.", "with", "from", "into", "onto", "over", "than"}


def _cap(word):
    # capitalize the first letter of a plain lowercase word, keeping any leading punctuation
    m = re.match(r"^([^A-Za-z0-9]*)([a-z])(.*)$", word)
    if not m:
        return word
    pre, first, rest = m.groups()
    if any(ch.isupper() for ch in rest):  # mixed case like iPhone: leave as is
        return word
    return pre + first.upper() + rest


def _core(word):
    return re.sub(r"^[^A-Za-z0-9$]+|[^A-Za-z0-9.]+$", "", word).lower()


def tc(text):
    if not text:
        return text
    tokens = re.split(r"(\s+)", text)
    words = [i for i, t in enumerate(tokens) if t.strip()]
    out = list(tokens)
    force_next = True
    for n, i in enumerate(words):
        w = tokens[i]
        # first word, last word, and the words on either side of a colon or semicolon are capitalized
        first_or_last = force_next or n == len(words) - 1 or bool(re.search(r"[:;]$", w))
        core = _core(w)
        if re.search(r"/|\.[a-z]", w) and core not in ("vs.",):
            new = w  # file paths and code names stay as written
        elif "-" in w.strip("-"):
            ps = w.split("-")
            new = "-".join(p if (not p or any(ch.isupper() for ch in p[1:])) else
                           (p.lower() if (0 < k < len(ps) - 1 and p.lower() in SMALL) else _cap(p)) for k, p in enumerate(ps))
        elif any(ch.isupper() for ch in w) or not re.search(r"[a-z]", w) or re.match(r"^[^A-Za-z]*[0-9$]", w):
            new = w  # acronyms, proper nouns, numbers and money stay as written
        elif core in SMALL and not first_or_last:
            new = w.lower()
        else:
            new = _cap(w)
        out[i] = new
        force_next = bool(re.search(r"[:;?!–—]$", w)) or w in ("-", "–", "—")
    return "".join(out)


if __name__ == "__main__":
    for s in ["Introduction: purpose, scope and stakeholders", "U.S. ISBN output by segment, 2022 to 2025 (stacked)",
              "Self-published ISBNs rose 38.7% in 2025.", "Cost variance vs Amazon KDP by driver, $ per print copy",
              "A. Independent creator", "Where the numbers come from.", "KPIs, part 1: money kept per sale and breakeven.",
              "Year-1 net by sales level (10, 50 and 250 sales of each format a month)", "how the story follows a launch",
              "Choose this when", "Gross-to-net: where each $16.99 goes", "A/B test design: the breakeven lift sets the bar"]:
        print(tc(s))
