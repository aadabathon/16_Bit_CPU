"""Check that every relative link and image in the markdown resolves.

Covers the top-level README, ROADMAP, demo, CONTRIBUTING and CHANGELOG, and
everything under docs/. A link to a heading
(file.md#anchor) must match a heading in the target file, using GitHub's
anchor rules (lower-case, punctuation dropped, spaces to hyphens).

    python3 check_links.py        exit 1 if anything is broken
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))


def anchors(path):
    out, counts, in_code = set(), {}, False
    for line in open(path):
        if line.startswith("```"):
            in_code = not in_code
        if in_code:
            continue
        m = re.match(r"^(#{1,6})\s+(.*)", line)
        if m:
            slug = re.sub(r"[^\w\- ]", "", m.group(2).strip().lower()).replace(" ", "-")
            n = counts.get(slug, 0)
            counts[slug] = n + 1
            out.add(slug if n == 0 else f"{slug}-{n}")
    return out


def main():
    files = [os.path.join(ROOT, f) for f in
             ("README.md", "ROADMAP.md", "demo.md", "CONTRIBUTING.md", "CHANGELOG.md")]
    for d, _, fs in os.walk(os.path.join(ROOT, "docs")):
        files += [os.path.join(d, f) for f in fs if f.endswith(".md")]
    bad, n = [], 0
    for f in sorted(files):
        text = re.sub(r"```.*?```", "", open(f).read(), flags=re.S)
        for m in re.finditer(r"\]\(([^)\s]+)\)", text):
            target = m.group(1)
            if re.match(r"[a-z]+:", target):
                continue
            n += 1
            path, _, anchor = target.partition("#")
            full = os.path.normpath(os.path.join(os.path.dirname(f), path)) if path else f
            rel = os.path.relpath(f, ROOT)
            if not os.path.exists(full):
                bad.append(f"{rel}: missing file {target}")
            elif anchor and full.endswith(".md") and anchor not in anchors(full):
                bad.append(f"{rel}: missing heading #{anchor} in {path or 'this file'}")
    if bad:
        print("broken links:")
        for b in bad:
            print("  -", b)
        sys.exit(1)
    print(f"links: {n} relative links and images resolve")


if __name__ == "__main__":
    main()
