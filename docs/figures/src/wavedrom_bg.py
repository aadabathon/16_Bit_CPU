"""Give a WaveDrom SVG an opaque white background (readable in dark mode).

usage: python3 wavedrom_bg.py file.svg
"""
import sys

path = sys.argv[1]
svg = open(path).read()
tag = 'class="WaveDrom">'
bg = '<rect width="100%" height="100%" fill="white"/>'
if bg not in svg:
    svg = svg.replace(tag, tag + bg, 1)
    open(path, "w").write(svg)
