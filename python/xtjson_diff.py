#!/usr/bin/env python3
"""Compare two LCHarvest2 exports: the original and the harvest of its rebuild.

    python3 xtjson_diff.py XTJSON XTJSON_REBUILT [--prefix XT_] [--out xtjson_diff.txt] [--max 40]

Stacks are matched by name (the prefix is removed from the second export's
names), cards by id (then by number), controls by id (then by type + name).
Properties are compared after resolving each side through its own
typeDefaults, so a difference means the real value differs, not just the
way it was written down.

Standard library only.
"""
import argparse
import collections
import hashlib
import json
import os
import sys


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


class Harvest:
    def __init__(self, folder, prefix=""):
        self.folder = folder
        self.prefix = prefix
        self.manifest = load_json(os.path.join(folder, "manifest.json"))
        self.defaults = self.manifest.get("typeDefaults") or {}
        self.sparse = bool((self.manifest.get("options") or {}).get("sparse", True))
        self.stacks = {}
        for entry in self.manifest.get("stacks", []):
            data = load_json(os.path.join(folder, entry["file"]))
            self.stacks[self.strip(data.get("name", entry["name"]))] = data

    def strip(self, name):
        if self.prefix and isinstance(name, str) and name.startswith(self.prefix):
            return name[len(self.prefix):]
        return name

    def read(self, rel, binary=False):
        path = os.path.join(self.folder, rel)
        if not os.path.isfile(path):
            return None
        with open(path, "rb") as f:
            data = f.read()
        if binary:
            return hashlib.sha1(data).hexdigest()[:12] + " (%d bytes)" % len(data)
        return data.decode("utf-8", "replace").replace("\r\n", "\n").replace("\r", "\n")

    def props(self, node):
        """Real property values: typeDefaults overlaid with the node's props."""
        out = {}
        if self.sparse:
            out.update(self.defaults.get(node.get("type"), {}))
        out.update(node.get("props") or {})
        return {k: v for k, v in out.items() if v not in ("", None)}

    def value(self, v):
        """Resolve {$file} markers so file names never count as differences."""
        if isinstance(v, dict):
            if "$file" in v:
                got = self.read(v["$file"], binary=bool(v.get("$binary")))
                return got if got is not None else "<missing file %s>" % v["$file"]
            return {k: self.value(x) for k, x in v.items()}
        if isinstance(v, list):
            return [self.value(x) for x in v]
        return v

    def script(self, node):
        s = node.get("script")
        if not s:
            return ""
        if "text" in s:
            return s["text"].replace("\r\n", "\n")
        got = self.read(s.get("file", ""))
        return got if got is not None else "<missing file %s>" % s.get("file")

    def behavior(self, node):
        b = node.get("behavior") or ""
        src = self.manifest.get("sourceFile") or ""
        if src:
            b = b.replace('stack "%s"' % src, 'stack "%s"' % self.strip(self.manifest.get("mainStack", "")))
        if self.prefix:
            b = b.replace('stack "%s' % self.prefix, 'stack "')
        return b


def flatten(controls, parent=None, path="", out=None):
    """Pre-order list of (node, parent id, path, position among siblings)."""
    if out is None:
        out = []
    for i, node in enumerate(controls or [], 1):
        here = "%s/%s '%s' #%s" % (path, node.get("type"), node.get("name", ""), node.get("id"))
        out.append((node, parent, here, i))
        if node.get("controls"):
            flatten(node["controls"], node.get("id"), here, out)
    return out


def short(v, n=70):
    s = json.dumps(v, ensure_ascii=False) if not isinstance(v, str) else repr(v)
    return s if len(s) <= n else s[: n - 3] + "..."


def same(a, b):
    if a == b:
        return True
    # 1 vs 1.0, "5" vs 5, [1,2] vs "1,2": LiveCode has no types, so these are equal
    def norm(v):
        if isinstance(v, bool):
            return "true" if v else "false"
        if isinstance(v, (int, float)):
            return ("%f" % v).rstrip("0").rstrip(".")
        if isinstance(v, list) and all(not isinstance(x, (list, dict)) for x in v):
            return ",".join(norm(x) for x in v)
        if isinstance(v, str):
            try:
                return norm(float(v)) if v.strip() == v and v else v
            except ValueError:
                return v.lower() if v.lower() in ("true", "false") else v
        return v
    return norm(a) == norm(b)


class Report:
    def __init__(self, limit):
        self.limit = limit
        self.items = collections.OrderedDict()   # category -> [lines]
        self.props = collections.Counter()        # "type.prop" -> count
        self.compared = collections.Counter()

    def add(self, category, where, detail):
        self.items.setdefault(category, []).append("%s: %s" % (where, detail))

    def total(self):
        return sum(len(v) for v in self.items.values())

    def text(self, a, b):
        lines = ["XTJSON diff", "A (original): " + a.folder, "B (rebuilt):  " + b.folder, ""]
        lines.append("compared: " + ", ".join("%d %s" % (n, k) for k, n in self.compared.items()))
        lines.append("differences: %d" % self.total())
        lines.append("")
        lines.append("BY CATEGORY")
        for cat, v in sorted(self.items.items(), key=lambda kv: -len(kv[1])):
            lines.append("  %6d  %s" % (len(v), cat))
        if self.props:
            lines.append("")
            lines.append("PROPERTIES THAT DIFFER MOST (type.property, count)")
            for key, n in self.props.most_common(40):
                lines.append("  %6d  %s" % (n, key))
        for cat, v in self.items.items():
            lines.append("")
            lines.append("== %s (%d)" % (cat, len(v)))
            for line in v[: self.limit]:
                lines.append("  " + line)
            if len(v) > self.limit:
                lines.append("  ... %d more (raise --max to see them)" % (len(v) - self.limit))
        return "\n".join(lines) + "\n"


def compare_node(rep, a, b, na, nb, where, kind):
    """Everything two matched objects (stack, card or control) have in common."""
    rep.compared[kind + "s"] += 1
    for key in ("type", "name", "kind", "number", "size"):
        va, vb = na.get(key), nb.get(key)
        if key == "name" and kind == "stack":
            vb = b.strip(vb)
        if not same(va, vb):
            rep.add(key, where, "%s -> %s" % (short(va), short(vb)))
    if kind == "control":
        for key in ("rect", "layer"):
            if not same(na.get(key), nb.get(key)):
                rep.add(key, where, "%s -> %s" % (short(na.get(key)), short(nb.get(key))))
        if bool(na.get("sharedRef")) != bool(nb.get("sharedRef")):
            rep.add("shared group", where, "sharedRef %s -> %s" % (na.get("sharedRef"), nb.get("sharedRef")))
    # built-in properties
    pa, pb = a.props(na), b.props(nb)
    for key in sorted(set(pa) | set(pb)):
        va, vb = pa.get(key, ""), pb.get(key, "")
        if kind == "stack" and key in ("visible", "mainStack"):
            continue
        if not same(va, vb):
            rep.props["%s.%s" % (na.get("type"), key)] += 1
            rep.add("property", where, "%s: %s -> %s" % (key, short(va), short(vb)))
    # content
    for key in ("text", "htmlText", "points"):
        va, vb = a.value(na.get(key)), b.value(nb.get(key))
        if not same(va, vb):
            rep.add(key, where, "%s -> %s" % (short(va), short(vb)))
    if ("asset" in na) or ("asset" in nb):
        ha = a.read(na["asset"], True) if na.get("asset") else None
        hb = b.read(nb["asset"], True) if nb.get("asset") else None
        if ha != hb:
            rep.add("image data", where, "%s -> %s" % (ha, hb))
    # custom properties
    ca, cb = a.value(na.get("custom") or {}), b.value(nb.get("custom") or {})
    sets_a, sets_b = ca.pop("$sets", {}) or {}, cb.pop("$sets", {}) or {}
    for label, da, db in [("", ca, cb)] + [(s + ".", sets_a.get(s, {}), sets_b.get(s, {})) for s in sorted(set(sets_a) | set(sets_b))]:
        for key in sorted(set(da) | set(db)):
            if key not in db:
                rep.add("custom property", where, "%s%s lost (was %s)" % (label, key, short(da[key])))
            elif key not in da:
                rep.add("custom property", where, "%s%s appeared (%s)" % (label, key, short(db[key])))
            elif not same(da[key], db[key]):
                rep.add("custom property", where, "%s%s: %s -> %s" % (label, key, short(da[key]), short(db[key])))
    # script and behavior
    sa, sb = a.script(na), b.script(nb)
    if sa != sb:
        if sa.rstrip() == sb.rstrip():
            rep.add("script (trailing whitespace only)", where, "%d -> %d lines" % (sa.count("\n") + 1, sb.count("\n") + 1))
        else:
            la, lb = sa.split("\n"), sb.split("\n")
            first = next((i for i, (x, y) in enumerate(zip(la, lb), 1) if x != y), min(len(la), len(lb)) + 1)
            rep.add("script", where, "%d -> %d lines, first difference at line %d" % (len(la), len(lb), first))
    if a.behavior(na) != b.behavior(nb):
        rep.add("behavior", where, "%s -> %s" % (short(a.behavior(na)), short(b.behavior(nb))))


def match(list_a, list_b, key_fns):
    """Pair items of two lists using each key function in turn. Returns pairs, only_a, only_b."""
    pairs, rest_a, rest_b = [], list(list_a), list(list_b)
    for fn in key_fns:
        index = collections.defaultdict(list)
        for item in rest_b:
            index[fn(item)].append(item)
        still_a = []
        for item in rest_a:
            bucket = index.get(fn(item))
            if bucket:
                other = bucket.pop(0)
                rest_b.remove(other)
                pairs.append((item, other))
            else:
                still_a.append(item)
        rest_a = still_a
    return pairs, rest_a, rest_b


def compare_card(rep, a, b, ca, cb, where):
    compare_node(rep, a, b, ca, cb, where, "card")
    fa, fb = flatten(ca.get("controls")), flatten(cb.get("controls"))
    pairs, only_a, only_b = match(
        fa, fb,
        [lambda t: ("id", t[0].get("id")),
         lambda t: ("name", t[0].get("type"), t[0].get("name"), t[1])])
    for node, _, path, _ in only_a:
        rep.add("control missing in rebuild", where, path)
    for node, _, path, _ in only_b:
        rep.add("control only in rebuild", where, path)
    for (na, parent_a, path, pos_a), (nb, parent_b, _, pos_b) in pairs:
        here = where + path
        if na.get("id") != nb.get("id"):
            rep.add("id", here, "%s -> %s" % (na.get("id"), nb.get("id")))
        if parent_a != parent_b:
            rep.add("parent group", here, "in #%s -> in #%s" % (parent_a, parent_b))
        elif pos_a != pos_b:
            rep.add("order among siblings", here, "position %d -> %d" % (pos_a, pos_b))
        compare_node(rep, a, b, na, nb, here, "control")
    # the plain back-to-front sequence, which is what the eye sees
    seq_a = [t[0].get("id") for t in fa]
    seq_b = [t[0].get("id") for t in fb]
    if seq_a != seq_b and sorted(map(str, seq_a)) == sorted(map(str, seq_b)):
        first = next(i for i, (x, y) in enumerate(zip(seq_a, seq_b), 1) if x != y)
        rep.add("card stacking order", where, "same controls, different order from position %d: #%s -> #%s" % (first, seq_a[first - 1], seq_b[first - 1]))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("original")
    ap.add_argument("rebuilt")
    ap.add_argument("--prefix", default="XT_", help="stack name prefix used by the rebuild (default XT_)")
    ap.add_argument("--out", default="xtjson_diff.txt")
    ap.add_argument("--max", type=int, default=40, help="lines shown per category")
    args = ap.parse_args()

    a, b = Harvest(args.original), Harvest(args.rebuilt, args.prefix)
    rep = Report(args.max)

    for kind in sorted(set(a.defaults) | set(b.defaults)):
        da, db = a.defaults.get(kind, {}), b.defaults.get(kind, {})
        for key in sorted(set(da) | set(db)):
            if not same(da.get(key, ""), db.get(key, "")):
                rep.add("typeDefaults (session templates differed)", kind, "%s: %s -> %s" % (key, short(da.get(key, "")), short(db.get(key, ""))))

    for name in sorted(set(a.stacks) | set(b.stacks)):
        if name not in b.stacks:
            rep.add("stack missing in rebuild", name, "")
            continue
        if name not in a.stacks:
            rep.add("stack only in rebuild", name, "")
            continue
        sa, sb = a.stacks[name], b.stacks[name]
        compare_node(rep, a, b, sa, sb, "stack '%s'" % name, "stack")
        pairs, only_a, only_b = match(
            sa.get("cards", []), sb.get("cards", []),
            [lambda c: ("id", c.get("id")), lambda c: ("number", c.get("number"))])
        for c in only_a:
            rep.add("card missing in rebuild", name, "card '%s' #%s" % (c.get("name"), c.get("id")))
        for c in only_b:
            rep.add("card only in rebuild", name, "card '%s' #%s" % (c.get("name"), c.get("id")))
        for ca, cb in pairs:
            where = "%s|card %s '%s'" % (name, ca.get("number"), ca.get("name"))
            if ca.get("id") != cb.get("id"):
                rep.add("id", where, "card id %s -> %s" % (ca.get("id"), cb.get("id")))
            compare_card(rep, a, b, ca, cb, where)

    text = rep.text(a, b)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(text)
    head = text.split("\n== ")[0]
    print(head)
    print("full report: " + args.out)
    return 0 if rep.total() == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
