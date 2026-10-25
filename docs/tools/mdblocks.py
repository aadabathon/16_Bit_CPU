"""Replace generated blocks inside markdown files.

A block looks like:

    <!-- BEGIN GENERATED: name -->
    ...anything...
    <!-- END GENERATED: name -->

Generators call update(path, {name: content}, check). In check mode nothing
is written; the return value says whether the file was already up to date.
"""

import re


def update(path, blocks, check=False):
    text = open(path).read()
    new = text
    for name, content in blocks.items():
        pat = re.compile(rf"(<!-- BEGIN GENERATED: {re.escape(name)} -->)\n.*?"
                         rf"(<!-- END GENERATED: {re.escape(name)} -->)", re.S)
        if not pat.search(new):
            raise KeyError(f"{path}: no generated block '{name}'")
        new = pat.sub(lambda m: m.group(1) + "\n" + content + "\n" + m.group(2), new)
    if new != text and not check:
        with open(path, "w") as f:
            f.write(new)
    return new == text
