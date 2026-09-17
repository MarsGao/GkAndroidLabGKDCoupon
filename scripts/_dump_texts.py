#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
import sys
from pathlib import Path

p = Path(sys.argv[1])
out = Path(sys.argv[2]) if len(sys.argv) > 2 else p.with_suffix(".texts.txt")
t = p.read_text(encoding="utf-8", errors="replace")
lines = []
lines.append(f"len={len(t)} nodes={t.count('<node')}")
for kind, pat in (("text", r'text="([^"]*)"'), ("desc", r'content-desc="([^"]*)"')):
    vals = [m for m in re.findall(pat, t) if m]
    lines.append(f"== {kind} count={len(vals)} ==")
    for v in vals:
        lines.append(v)
out.write_text("\n".join(lines), encoding="utf-8")
print(out)
