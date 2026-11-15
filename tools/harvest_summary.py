#!/usr/bin/env python3
"""harvest_summary.py - a short, readable summary of LiveCode harvests (XTJSON format 2), so a
person or an AI can understand a stack without reading its JSON.

  python3 -I harvest_summary.py HARVEST_DIR [HARVEST_DIR ...]      (a dir that holds manifest.json)
  python3 -I harvest_summary.py --tree BATCH_DIR                   (every harvest under it)

For each stack: cards, control counts by type, named controls, every handler (with the script it
is in and its size), custom properties and property sets (keys, sizes), and the first lines of the
longest field texts. Read-only.
"""
import json, os, sys
from collections import Counter

MAX_TEXT_LINES = 4


def walk_controls(ctls, out):
    for c in ctls or []:
        out.append(c)
        walk_controls(c.get('controls'), out)


def text_of(base, t):
    if isinstance(t, dict) and '$file' in t:
        try:
            return open(os.path.join(base, t['$file']), encoding='utf-8', errors='replace').read()
        except OSError:
            return ''
    return t if isinstance(t, str) else ''


def custom_summary(cu):
    if not cu:
        return []
    out = []
    for k, v in cu.items():
        if k == '$sets':
            for sname, sv in (v or {}).items():
                keys = list(sv.keys()) if isinstance(sv, dict) else []
                out.append('set %s: %d keys (%s)' % (sname, len(keys), ', '.join(keys[:8]) + (' ...' if len(keys) > 8 else '')))
        else:
            size = len(json.dumps(v))
            out.append('%s (%d chars)' % (k, size))
    return out


def handlers(obj):
    s = obj.get('script') or {}
    return s.get('lines', 0), [h['name'] for h in s.get('handlers', [])]


def summarise(hdir):
    lines = []
    man = json.load(open(os.path.join(hdir, 'manifest.json')))
    lines.append('## %s' % os.path.relpath(hdir))
    lines.append('source: %s | harvested %s' % (os.path.basename(man.get('sourceFile', '?')), man.get('harvested', '?')))
    for st in man.get('stacks', []):
        path = os.path.join(hdir, st['file'])
        if not os.path.exists(path):
            continue
        d = json.load(open(path))
        n, hs = handlers(d)
        lines.append('### stack "%s" (%s): %d cards' % (d.get('name'), st.get('role'), len(d.get('cards', []))))
        if hs:
            lines.append('stack script %d lines, %d handlers: %s' % (n, len(hs), ', '.join(hs)))
        for c in custom_summary(d.get('custom')):
            lines.append('stack custom: ' + c)
        texts = []
        for card in d.get('cards', []):
            ctls = []
            walk_controls(card.get('controls'), ctls)
            kinds = Counter(c['type'] for c in ctls)
            cn, chs = handlers(card)
            lines.append('- card %s "%s": %s%s' % (card.get('number'), card.get('name', ''),
                         ', '.join('%d %s' % (v, k) for k, v in kinds.most_common()) or 'no controls',
                         ('; card script %d lines: %s' % (cn, ', '.join(chs))) if chs else ''))
            for c in custom_summary(card.get('custom')):
                lines.append('  card custom: ' + c)
            for c in ctls:
                cn, chs = handlers(c)
                if chs and cn > 3:
                    lines.append('  %s "%s" script %d lines: %s' % (c['type'], c.get('name', ''), cn, ', '.join(chs)))
                t = text_of(hdir, c.get('text'))
                if t.strip():
                    texts.append((len(t), c.get('name', ''), t))
                for cc in custom_summary(c.get('custom')):
                    lines.append('  %s "%s" custom: %s' % (c['type'], c.get('name', ''), cc))
        for size, name, t in sorted(texts, reverse=True)[:5]:
            first = [l for l in t.splitlines() if l.strip()][:MAX_TEXT_LINES]
            lines.append('  field "%s" (%d chars): %s' % (name, size, ' | '.join(l[:90] for l in first)))
    return '\n'.join(lines)


def main(argv):
    if not argv:
        print(__doc__)
        return 1
    dirs = []
    if argv[0] == '--tree':
        for root, _, files in os.walk(argv[1]):
            if 'manifest.json' in files:
                dirs.append(root)
    else:
        dirs = argv
    for d in sorted(dirs):
        try:
            print(summarise(d))
        except Exception as e:                       # one bad harvest must not stop the rest
            print('## %s\nFAILED: %s' % (d, e))
        print()
    return 0


if __name__ == '__main__':
    if any(a in ('-h', '--help') for a in sys.argv[1:]):   # A-50: every tool answers --help
        print(__doc__)
        sys.exit(0)
    sys.exit(main(sys.argv[1:]))
