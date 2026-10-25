"""Draw the control FSM bubble diagrams and write RTL conformance vectors.

    python3 gen_fsm.py                      # all diagrams -> docs/figures/fsm_*.svg
    python3 gen_fsm.py --vectors FILE       # vectors for tb/tb_control_fsm_spec.sv
    python3 gen_fsm.py --dot DIR            # also keep the Graphviz sources

Everything comes from fsm_spec.py; see that file for the notation.
"""

import argparse
import html
import os
import random
import subprocess
import sys

import mdblocks
from fsm_spec import (ARCS, CODE_NAMES, DEFAULTS, OP, OUTPUTS, RESET_STATE, SHOW, STATE,
                      STATES, WIDTH, Expr, In, instruction_trace, pack, step)

HERE = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.normpath(os.path.join(HERE, "..", "figures"))
CONTROL_DOC = os.path.normpath(os.path.join(HERE, "..", "03_control.md"))

FILL = {"fetch": "#e0ecff", "decode": "#e0ecff", "execute": "#f5f7fb", "memory": "#fff4e0"}
GREY = "#94a3b8"
MONO = "Courier"


# --------------------------------------------------------------------------
# Labels
# --------------------------------------------------------------------------
def esc(s):
    return html.escape(s, quote=False)


def fmt_out(name, v):
    if isinstance(v, Expr):
        return f"{name}={v.text}"
    if WIDTH[name] == 1:
        return name if v == 1 else f"{name}=0"
    meaning = CODE_NAMES.get(name, {}).get(v)
    return f"{name}={v:0{WIDTH[name]}b}" + (f" ({meaning})" if meaning else "")


def wrap_cond(text, limit=30):
    """Break a long condition after commas: 'op ∈ {A, B, C}' -> two lines."""
    if len(text) <= limit:
        return [text]
    lines, cur = [], ""
    for part in text.split(", "):
        nxt = f"{cur}, {part}" if cur else part
        if cur and len(nxt) > limit:
            lines.append(cur + ",")
            cur = "    " + part
        else:
            cur = nxt
    return lines + [cur]


def pack_lines(items, limit=28):
    lines, cur = [], ""
    for it in items:
        if cur and len(cur) + 2 + len(it) > limit:
            lines.append(cur)
            cur = it
        else:
            cur = f"{cur}, {it}" if cur else it
    if cur:
        lines.append(cur)
    return lines


def arc_label(arc, with_outputs=True):
    order = [n for n, _ in OUTPUTS]
    items = sorted(arc.out.items(), key=lambda kv: order.index(kv[0]))
    asserted = [fmt_out(k, v) for k, v in items if isinstance(v, Expr) or v != DEFAULTS[k]]
    sig_def = [fmt_out(k, v) for k, v in items if not isinstance(v, Expr) and v == DEFAULTS[k]]
    cond = arc.when.text if arc.when else ""
    if not with_outputs:
        asserted, sig_def = [], []
    rows = [f"<b>{esc(l)}</b>" for l in wrap_cond(cond)] if cond else []
    out_rows = [(l, None) for l in pack_lines(asserted)] + [(l, GREY) for l in pack_lines(sig_def)]
    for k, (l, color) in enumerate(out_rows):
        text = esc(("/ " if k == 0 else "  ") + l)
        c = f' color="{color}"' if color else ""
        rows.append(f'<font face="{MONO}"{c}>{text}</font>')
    if not rows:
        return ""
    body = "".join(f'<tr><td align="left">{r}</td></tr>' for r in rows)
    return f'<<table border="0" cellborder="0" cellspacing="0" cellpadding="1">{body}</table>>'


def bubble(st, star=False, rtl=True, size=1.4):
    lines = [f"<b>{esc(st.name)}</b>"]
    if rtl:
        rtl_lines = st.rtl.split("\n")
        if star:
            rtl_lines[-1] += " *"
        lines += [f'<font point-size="9.5">{esc(l)}</font>' for l in rtl_lines]
    label = "<" + "<br/>".join(lines) + ">"
    return (f'  "{st.name}" [label={label}, fillcolor="{FILL[st.phase]}", '
            f'width={size}, height={size}];')


def conditional_states():
    """States whose outputs differ between arcs (outputs depend on IR / flags)."""
    out = set()
    for st in STATES:
        outs = {tuple(sorted((k, str(v)) for k, v in a.out.items())) for a in ARCS if a.src == st.name}
        if len(outs) > 1:
            out.add(st.name)
    return out


HEADER = """digraph {name} {{
  graph [bgcolor="white", rankdir={rankdir}, nodesep={nodesep}, ranksep={ranksep}, pad=0.3,
         fontname="Helvetica", fontsize=13, newrank=true, labelloc=t, label=<{title}>];
  node  [shape=circle, fixedsize=true, style=filled, color="#334155", penwidth=1.4,
         fontname="Helvetica", fontsize=10.5];
  edge  [color="#334155", fontname="Helvetica", fontsize=10, arrowsize=0.75, penwidth=1.1];
"""

NOTE = ('  note [shape=box, style="rounded,dashed", fixedsize=false, color="#64748b", '
        'fillcolor="white", fontsize=9.5, margin="0.15,0.08", label=<{body}>];')


def note_body(extra=()):
    rows = ["<b>Notation</b>",
            "<b>condition</b>",
            f'<font face="{MONO}">/ outputs</font>  driven while in the source state',
            "outputs not listed are 0",
            f'<font face="{MONO}" color="{GREY}">grey</font> = a default value that matters',
            "dashed bubble = state drawn in another diagram"]
    rows += list(extra)
    body = "".join(f'<tr><td align="left">{r}</td></tr>' for r in rows)
    return f'<table border="0" cellborder="0" cellspacing="0" cellpadding="1">{body}</table>' 


def connector(node_id, text):
    return (f'  "{node_id}" [label="{text}", shape=circle, style="dashed", fillcolor="white", '
            f'fontcolor="#475569", color="#64748b", width=1.0, height=1.0, fontsize=9.5];')


# --------------------------------------------------------------------------
# Overview
# --------------------------------------------------------------------------
def overview():
    star = conditional_states()
    d = [HEADER.format(name="overview", rankdir="TB", nodesep=0.35, ranksep=0.55,
                       title="<b>cpu16_control_fsm</b>  overview")]
    d.append('  rst [shape=plaintext, style="", fixedsize=false, width=0, '
             'label="rst\\n(any state,\\nsynchronous)", fontsize=10];')
    defaults = "<br/>".join(
        ["<b>Default outputs (every state)</b>"]
        + pack_lines([f"{n} = 0" for n, _ in OUTPUTS], 44)
        + ["<i>* = outputs depend on IR or N/Z/P</i>",
           "<i>full condition / output arcs: detail diagrams</i>"])
    d.append(NOTE.replace("note", "defaults", 1).format(body=defaults))
    for st in STATES:
        d.append(bubble(st, star=st.name in star))
    d.append('  { rank=same; rst; "S_IF0"; "S_IF1"; "S_IF2"; "S_ID"; }')
    d.append('  { rank=same; "S_EX_ALU"; "S_EX_EA"; "S_EX_BR"; "S_EX_JMP"; "S_EX_JSR"; "S_EX_TRAP"; }')
    d.append('  { rank=same; "S_MEM_RD0"; "S_MEM_RD1"; "S_WB_LD"; "S_MEM_WR0"; }')
    d.append('  rst -> "S_IF0" [style=bold];')
    d.append('  back [shape=point, width=0.08, style=filled, fillcolor="#334155", label=""];')

    groups = {}
    for a in ARCS:
        groups.setdefault((a.src, a.dst), []).append(a)
    for (src, dst), arcs in groups.items():
        n_dst = len({a.dst for a in ARCS if a.src == src})
        label = ", ".join(a.brief for a in arcs if a.brief) if n_dst > 1 else ""
        lab = f' [label="{label}"]' if label else ""
        if dst == RESET_STATE and src == "S_ID":
            d.append(f'  "{src}" -> "{dst}" [label="{label}", style=dashed, constraint=false];')
        elif dst == RESET_STATE:
            d.append(f'  "{src}" -> back [arrowhead=none];')
        else:
            d.append(f'  "{src}" -> "{dst}"{lab};')
    d.append('  back -> "S_IF0" [label="  next\\n  instruction", constraint=false, penwidth=1.6];')
    d.append('  "S_WB_LD" -> "S_MEM_WR0" [style=invis];')
    d.append("  { rank=sink; back; defaults; }")
    d.append("}")
    return "\n".join(d)


# --------------------------------------------------------------------------
# Detail diagrams: real bubbles for `states`, dashed connectors elsewhere
# --------------------------------------------------------------------------
def detail(name, title, states, entry_text=None, nodesep=0.25, ranksep=0.7, extra_note=(),
           order_rows=False):
    inside = set(states)
    d = [HEADER.format(name=name, rankdir="LR", nodesep=nodesep, ranksep=ranksep, title=title)]
    d.append(NOTE.format(body=note_body(extra_note)))
    for s in states:
        d.append(bubble(STATE[s]))

    # arcs entering from outside
    entering = [a for a in ARCS if a.dst in inside and a.src not in inside]
    by_dst = {}
    for a in entering:
        by_dst.setdefault(a.dst, []).append(a)
    k = 0
    for dst, arcs in by_dst.items():
        srcs = {a.src for a in arcs}
        if len(srcs) > 2:      # e.g. every execute path returning to fetch
            nid = f"in{k}"; k += 1
            d.append(connector(nid, entry_text or "from\\nexecute"))
            d.append(f'  "{nid}" -> "{dst}" [style=dashed];')
            continue
        for a in arcs:
            nid = f"in{k}"; k += 1
            d.append(connector(nid, a.src))
            lab = arc_label(a, with_outputs=False)
            d.append(f'  "{nid}" -> "{dst}"' + (f" [label={lab}]" if lab else "") + ";")

    if order_rows and k > 1:   # keep the entry rows in spec order, top to bottom
        chain = " -> ".join(f'"in{i}"' for i in range(k))
        d.append(f"  {{ rank=same; {chain} [style=invis]; }}")

    # arcs leaving states inside the diagram
    for i, a in enumerate(x for x in ARCS if x.src in inside):
        lab = arc_label(a)
        attrs = f" [label={lab}]" if lab else ""
        if a.dst in inside:
            d.append(f'  "{a.src}" -> "{a.dst}"{attrs};')
        else:
            nid = f"out{i}"
            d.append(connector(nid, a.dst))
            d.append(f'  "{a.src}" -> "{nid}"{attrs};')
    d.append("}")
    return "\n".join(d)


INPUTS_NOTE = ["", "<b>Inputs</b>", "op = IR[15:12]    fn = IR[2:0]",
               "DR = IR[11:9]     j = IR[11]"]

DIAGRAMS = {
    "fsm_overview": overview,
    "fsm_fetch": lambda: detail(
        "fetch", "<b>Fetch and decode</b>  (S_IF0 – S_ID)",
        ["S_IF0", "S_IF1", "S_IF2", "S_ID"], entry_text="end of every\\ninstruction",
        extra_note=INPUTS_NOTE + ["rst (synchronous) → S_IF0 from any state"]),
    "fsm_alu": lambda: detail(
        "alu", "<b>ALU, immediate and LEA</b>  (S_EX_ALU)", ["S_EX_ALU"],
        nodesep=0.12, ranksep=1.2, extra_note=INPUTS_NOTE),
    "fsm_mem": lambda: detail(
        "mem", "<b>Loads and stores</b>  (S_EX_EA – S_MEM_WR0)",
        ["S_EX_EA", "S_MEM_RD0", "S_MEM_RD1", "S_WB_LD", "S_MEM_WR0"],
        ranksep=0.8, extra_note=INPUTS_NOTE),
    "fsm_flow": lambda: detail(
        "flow", "<b>Branches, jumps, calls and TRAP</b>",
        ["S_EX_BR", "S_EX_JMP", "S_EX_JSR", "S_EX_TRAP"], nodesep=0.18, ranksep=1.0,
        order_rows=True,
        extra_note=INPUTS_NOTE + ["take_br = (IR[11]&amp;N) | (IR[10]&amp;Z) | (IR[9]&amp;P)"]),
}


# --------------------------------------------------------------------------
# Markdown tables for docs/03_control.md
# --------------------------------------------------------------------------
def md(s):
    return s.replace("|", "\\|")


def next_text(st):
    arcs = [a for a in ARCS if a.src == st.name]
    dsts = list(dict.fromkeys(a.dst for a in arcs))
    if len(dsts) == 1:
        return f"`{dsts[0]}`"
    if st.name == "S_ID":
        return "by opcode ([decode table](#decode-next-state-from-s_id))"
    return ", ".join(f"`{d}` if " + "/".join(a.brief for a in arcs if a.dst == d) for d in dsts)


def states_table():
    rows = ["| State | Code | Phase | Register transfer (on the closing edge) | Next state |",
            "|---|---|---|---|---|"]
    for st in STATES:
        text = st.detail or st.rtl.replace("\n", ", ")
        rows.append(f"| `{st.name}` | {st.code} | {st.phase} | {md(text)} | {next_text(st)} |")
    return "\n".join(rows)


def decode_table():
    name_of = {v: SHOW.get(k, k) for k, v in OP.items()}
    groups = {}
    for op in range(16):
        _, dst = step("S_ID", In(op << 12, 0, 1, 0))
        groups.setdefault(dst, []).append(op)
    rows = ["| Opcode `IR[15:12]` | Instructions | Next state |", "|---|---|---|"]
    for dst, ops in groups.items():
        codes = ", ".join(f"`{o:04b}`" for o in ops)
        names = ", ".join(name_of[o] for o in ops)
        note = " (undefined: a 4-cycle no-op)" if dst == RESET_STATE else ""
        rows.append(f"| {codes} | {names} | `{dst}`{note} |")
    return "\n".join(rows)


def cell(name, arc):
    if name not in arc.out:
        return "·"
    v = arc.out[name]
    if isinstance(v, Expr):
        return f"`{v.text}`"
    return str(v) if WIDTH[name] == 1 else f"`{v:0{WIDTH[name]}b}`"


def control_table():
    names = [n for n, _ in OUTPUTS]
    head = "| State | Case | " + " | ".join(f"`{n}`" for n in names) + " | Next |"
    rows = [head, "|" + "---|" * (len(names) + 3)]
    for st in STATES:
        for k, a in enumerate(x for x in ARCS if x.src == st.name):
            first = f"`{st.name}`" if k == 0 else ""
            case = md(a.when.text) if a.when else ""
            rows.append(f"| {first} | {case} | " + " | ".join(cell(n, a) for n in names)
                        + f" | `{a.dst}` |")
    return "\n".join(rows)


def doc_blocks():
    return {"fsm-states": states_table(), "fsm-decode": decode_table(),
            "fsm-control-table": control_table()}


# --------------------------------------------------------------------------
# Conformance vectors
# --------------------------------------------------------------------------
def write_vectors(path, seed=551):
    """Every opcode x IR[11:9] x funct x {N,Z,P}, random IR[8:3], one line per cycle:
    ir nzp cycle state_code packed_outputs (hex, hex, dec, dec, hex)."""
    rng = random.Random(seed)
    n = 0
    with open(path, "w") as f:
        for op in range(16):
            for dr in range(8):
                for fn in range(8):
                    for nzp in range(8):
                        ir = (op << 12) | (dr << 9) | (rng.randrange(64) << 3) | fn
                        inp = In(ir, (nzp >> 2) & 1, (nzp >> 1) & 1, nzp & 1)
                        trace = instruction_trace(inp)
                        trace.append((RESET_STATE, step(RESET_STATE, inp)[0]))
                        for cyc, (st, outs) in enumerate(trace):
                            f.write(f"{ir:04x} {nzp:x} {cyc} {STATE[st].code} {pack(outs):07x}\n")
                        n += 1
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vectors")
    ap.add_argument("--dot", help="directory to also write .dot sources into")
    ap.add_argument("--check", action="store_true",
                    help="only check that the tables in 03_control.md are up to date")
    args = ap.parse_args()
    if args.check:
        if not mdblocks.update(CONTROL_DOC, doc_blocks(), check=True):
            print("03_control.md FSM tables are out of date\n  run: make -C docs")
            sys.exit(1)
        print("03_control.md: FSM tables up to date with fsm_spec.py")
        return
    if args.vectors:
        n = write_vectors(args.vectors)
        print(f"wrote {n} instruction traces to {args.vectors}")
        return
    for name, build in DIAGRAMS.items():
        src = build()
        if args.dot:
            with open(os.path.join(args.dot, name + ".dot"), "w") as f:
                f.write(src)
        svg = subprocess.run(["dot", "-Tsvg"], input=src.encode(), check=True,
                             capture_output=True).stdout
        with open(os.path.join(FIG, name + ".svg"), "wb") as f:
            f.write(svg)
        print("wrote", os.path.join("figures", name + ".svg"))
    mdblocks.update(CONTROL_DOC, doc_blocks())
    print("wrote FSM tables in 03_control.md")


if __name__ == "__main__":
    main()
