"""xtjson_harvest - harvest a LiveCode stack file to XTJSON from a terminal or an MCP tool,
and answer questions about a harvest without reading the raw JSON.

    python3 xtjson_harvest.py harvest STACKFILE [OUTFOLDER]
    python3 xtjson_harvest.py summary  HARVEST
    python3 xtjson_harvest.py handlers HARVEST [FILTER]
    python3 xtjson_harvest.py globals  HARVEST [FILTER]
    python3 xtjson_harvest.py custom   HARVEST [SET [KEY]]
    python3 xtjson_harvest.py script   HARVEST OBJECT [HANDLER]

Also used by `lcmcp harvest` (LIB_MCP) and the MCP tool pack mcp/xtjson_tools.py.

harvest drives LiveCode through LIB_MCP (the standalone on port 8767 by default, started
when needed). LCHarvest2.livecodescript is installed as the script of a hidden library
stack "XT_HarvestLib" on every call, so edits to the harvester apply at once and the file
stays pasteable (it has no `script "..."` header on purpose: xtReemder reads it as text).
The stack file is loaded with messages locked, so none of its own handlers run, and it
is removed from memory again afterwards unless it was already open. Nothing is saved.

HARVEST arguments may be a folder path or a bare name under ~/projects/XTJSON.
STACKFILE may be a WSL path, a Windows path or a \\\\wsl$ path.
Standard library only.
"""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)                                   # .../LIB_XTJSON
HARVESTER = os.path.join(REPO, 'livecode', 'LCHarvest2.livecodescript')
if not os.path.isfile(HARVESTER):      # kept as text by the owner (2026-11-13): either name works
    HARVESTER = os.path.join(REPO, 'livecode', 'LCHarvest2_livecodescript.txt')
HARVEST_ROOT = os.environ.get('XTJSON_HARVEST_ROOT', os.path.expanduser('~/projects/XTJSON'))
LIB_NAME = 'XT_HarvestLib'


def _import_lib_mcp():
    try:
        import lib_mcp.client  # noqa: F401
    except ImportError:
        lib = os.environ.get('LIB_MCP_DIR', os.path.join(os.path.dirname(REPO), 'LIB_MCP'))
        sys.path.insert(0, os.path.join(lib, 'python'))
    from lib_mcp import client
    return client


# ---------------------------------------------------------------------------- paths
def to_livecode_path(path):
    """any local / Windows / UNC path -> forward-slash path LiveCode on Windows can open.
    Works for paths that do not exist yet (wslpath does not)."""
    p = path.strip().strip('"')
    if p.startswith('\\\\') or p.startswith('//') or (len(p) > 1 and p[1] == ':'):
        return p.replace('\\', '/')
    p = os.path.abspath(os.path.expanduser(p))
    m = re.match(r'^/mnt/([a-z])(/.*)?$', p)
    if m:
        return m.group(1).upper() + ':' + (m.group(2) or '/')
    distro = os.environ.get('WSL_DISTRO_NAME')
    if distro:
        return '//wsl$/' + distro + p
    return p


def to_local_path(path):
    """LiveCode / Windows path -> path usable here"""
    p = path.strip().strip('"').replace('\\', '/')
    m = re.match(r'^//(wsl\$|wsl\.localhost)/[^/]+(/.*)$', p, re.I)
    if m and os.path.isdir('/mnt/c'):
        return m.group(2)
    if len(p) > 1 and p[1] == ':' and os.path.isdir('/mnt/c'):
        return '/mnt/' + p[0].lower() + p[2:]
    return os.path.expanduser(p)


def lc_string(s):
    if '"' in s or '\n' in s or '\r' in s:
        raise ValueError('path may not contain double quotes or line breaks: %r' % s)
    return '"' + s + '"'


def resolve_harvest(name):
    """folder path, or a bare name under HARVEST_ROOT"""
    for cand in (to_local_path(name), os.path.join(HARVEST_ROOT, name)):
        if os.path.isfile(os.path.join(cand, 'manifest.json')):
            return cand
    raise ValueError('No harvest (manifest.json) at %r or under %s' % (name, HARVEST_ROOT))


# ---------------------------------------------------------------------------- harvest
# Runs inside LIB_MCP's DevServer.Run through `do`, so it shares that handler's locals (tErr,
# tResult...): every name here starts with xh to avoid redeclaring one. No `exit`: it would
# leave the server handler too, and the reply would never be sent.
HARVEST_SCRIPT = r'''local xhSrc, xhOut, xhName, xhWasOpen, xhErr, xhFail
put %(src)s into xhSrc
put %(out)s into xhOut
put empty into xhFail
if there is not a file xhSrc then put "HARVEST FAILED: no stack file at" && xhSrc into xhFail
if xhFail is empty then
   if there is not a stack "%(lib)s" then
      lock messages
      create invisible stack "%(lib)s"
      unlock messages
   end if
   set the script of stack "%(lib)s" to url ("file:" & %(harvester)s)
   if the result is not empty then put "HARVEST FAILED: LCHarvest2 does not compile:" && the result into xhFail
end if
if xhFail is empty then
   start using stack "%(lib)s"
   put false into xhWasOpen
   repeat for each line xhMain in the mainStacks
      if the effective filename of stack xhMain is xhSrc then
         put true into xhWasOpen
         put xhMain into xhName
      end if
   end repeat
   if not xhWasOpen then
      lock messages
      put the short name of stack xhSrc into xhName
      unlock messages
   end if
   if xhName is empty then put "HARVEST FAILED: could not load" && xhSrc into xhFail
end if
if xhFail is empty then
   if xhOut is empty then
      harvestStack xhName
   else
      harvestStack xhName, xhOut
   end if
   put the result into xhErr
   put xhErr & cr & harvestErrors()
   if not xhWasOpen then
      lock messages
      delete stack xhName
      unlock messages
   end if
else
   put xhFail
end if
'''


def default_out(stack_path):
    base = os.path.splitext(os.path.basename(to_local_path(stack_path).replace('\\', '/')))[0]
    return os.path.join(HARVEST_ROOT, base)


def harvest(stack_path, out_folder=None, client=None, timeout=600):
    """returns (ok, text). out_folder None -> ~/projects/XTJSON/<file name>; '' -> harvester default"""
    if client is None:
        client = _import_lib_mcp().Client.standalone()
    if out_folder is None:
        out_folder = default_out(stack_path)
    if out_folder:
        os.makedirs(to_local_path(out_folder), exist_ok=True)
    code = HARVEST_SCRIPT.lstrip('\n') % {
        'src': lc_string(to_livecode_path(stack_path)),
        'out': lc_string(to_livecode_path(out_folder) if out_folder else ''),
        'harvester': lc_string(to_livecode_path(HARVESTER)),
        'lib': LIB_NAME,
    }
    ok, text = client.request('POST', '/run?in=server', code, timeout=timeout)
    text = text.strip()
    ok = ok and text.startswith('harvested')
    if ok and out_folder:
        try:
            text += '\n\n' + summary(out_folder)
        except (OSError, ValueError) as e:
            text += '\n(could not summarise: %s)' % e
    return ok, text


# ---------------------------------------------------------------------------- reading a harvest
def _load(folder):
    folder = resolve_harvest(folder)
    man = json.load(open(os.path.join(folder, 'manifest.json'), encoding='utf-8'))
    stacks = [json.load(open(os.path.join(folder, s['file']), encoding='utf-8')) for s in man['stacks']]
    return folder, man, stacks


def _walk(node, path=()):
    """yield (node, path-of-names) for stack, cards, controls"""
    yield node, path
    for c in node.get('cards', []):
        yield from _walk(c, path + ('card %s' % (c.get('name') or c.get('number')),))
    for c in node.get('controls', []):
        yield from _walk(c, path + ('%s "%s"' % (c['type'], c.get('name', '')),))


def _label(node):
    if node['type'] == 'stack':          # a stack's id is its next free object id, not a key
        return 'stack "%s"' % node.get('name', '')
    return '%s "%s" (id %s)' % (node['type'], node.get('name', ''), node.get('id'))


def summary(folder):
    folder, man, stacks = _load(folder)
    out = ['%s  (harvested %s, LiveCode %s)' % (man.get('mainStack'), man.get('harvested'), man.get('livecodeVersion')),
           'source: %s' % man.get('sourceFile'), 'folder: %s' % folder]
    counts = man.get('counts', {})
    out.append('counts: ' + ', '.join('%s %s' % (v, k) for k, v in counts.items() if v))
    if man.get('errors'):
        out.append('ERRORS: %d objects failed, see manifest.json "errors"' % len(man['errors']))
    for st in stacks:
        scripts = []
        for n, _ in _walk(st):
            s = n.get('script')
            if isinstance(s, dict) and s.get('lines'):
                scripts.append((s['lines'], len(s.get('handlers', [])), _label(n)))
        scripts.sort(reverse=True)
        out.append('\nstack %s (%s): %d cards' % (st['name'], st.get('role'), len(st.get('cards', []))))
        out.append('  biggest scripts (lines, handlers):')
        out += ['    %5d %4d  %s' % s for s in scripts[:8]]
        sets = []
        for n, _ in _walk(st):
            for setname, val in (n.get('custom') or {}).get('$sets', {}).items():
                sets.append('    %s / %s: %s' % (_label(n), setname,
                                                 '%d keys' % len(val) if isinstance(val, dict) else type(val).__name__))
        if sets:
            out.append('  custom property sets:')
            out += sets[:40]
    return '\n'.join(out)


def handlers(folder, filt=None, limit=400):
    folder, man, stacks = _load(folder)
    f = (filt or '').lower()
    out = []
    for st in stacks:
        for n, _ in _walk(st):
            s = n.get('script')
            if not isinstance(s, dict):
                continue
            for h in s.get('handlers', []):
                line = '%-34s %5d  %s %s %s' % (_label(n), h['line'], h['type'], h['name'], h.get('params', ''))
                if not f or f in line.lower():
                    out.append(line.rstrip())
    more = '' if len(out) <= limit else '\n... %d more, narrow with a filter' % (len(out) - limit)
    return ('\n'.join(out[:limit]) + more) or 'no handlers match'


def _script_text(folder, s):
    if 'text' in s:
        return s['text']
    return open(os.path.join(folder, s['file']), encoding='utf-8', errors='replace').read()


def globals_(folder, filt=None):
    """global declarations with their trailing comments, first comment wins"""
    folder, man, stacks = _load(folder)
    found, users = {}, {}
    for st in stacks:
        for n, _ in _walk(st):
            s = n.get('script')
            if not isinstance(s, dict):
                continue
            for line in _script_text(folder, s).splitlines():
                m = re.match(r'^\s*global\s+(.*)$', line, re.I)
                if not m:
                    continue
                body, _, comment = m.group(1).partition('--')
                for name in [x.strip() for x in body.split(',') if x.strip()]:
                    if not re.match(r'^[A-Za-z_][\w.]*$', name):
                        continue
                    if comment.strip() and not found.get(name):
                        found[name] = comment.strip()
                    found.setdefault(name, '')
                    users.setdefault(name, set()).add(_label(n))
    f = (filt or '').lower()
    rows = ['%-34s %3d obj  %s' % (k, len(users[k]), found[k]) for k in sorted(found, key=str.lower)
            if not f or f in k.lower() or f in found[k].lower()]
    return '%d globals\n' % len(rows) + '\n'.join(rows)


def _find_nodes(stacks, obj):
    obj = (obj or 'stack').lower()
    hits = []
    for st in stacks:
        for n, _ in _walk(st):
            if obj == 'stack' and n['type'] == 'stack':
                hits.append(n)
            elif obj == str(n.get('id')) or obj == (n.get('name') or '').lower() or obj == _label(n).lower():
                hits.append(n)
    return hits


def custom(folder, setname=None, key=None, obj=None, maxchars=6000):
    folder, man, stacks = _load(folder)
    nodes = _find_nodes(stacks, obj)
    if not nodes:
        return 'no object %r (use "stack", an id or a name)' % obj
    n = nodes[0]
    c = n.get('custom') or {}
    sets = c.get('$sets', {})
    if not setname:
        lines = ['%s custom properties:' % _label(n)]
        lines += ['  (default) %s = %s' % (k, json.dumps(v)[:100]) for k, v in c.items() if k != '$sets']
        lines += ['  set %s: %s' % (k, '%d keys' % len(v) if isinstance(v, dict) else json.dumps(v)[:80])
                  for k, v in sets.items()]
        return '\n'.join(lines)
    data = c if setname in ('', 'default') else sets.get(setname)
    if data is None:
        names = [k for k in sets if k.lower() == setname.lower()]
        data = sets.get(names[0]) if names else None
    if data is None:
        return 'no set %r on %s; sets: %s' % (setname, _label(n), ', '.join(sets) or 'none')
    if key:
        val = data.get(key) if isinstance(data, dict) else None
        if isinstance(val, dict) and '$file' in val:
            val = open(os.path.join(folder, val['$file']), encoding='utf-8', errors='replace').read()
        text = val if isinstance(val, str) else json.dumps(val, indent=1)
    elif isinstance(data, dict):
        text = '\n'.join('%s = %s' % (k, v if isinstance(v, str) else json.dumps(v)) for k, v in data.items())
    else:
        text = json.dumps(data)
    return text if len(text) <= maxchars else text[:maxchars] + '\n... (%d more chars)' % (len(text) - maxchars)


def script(folder, obj, handler=None, maxchars=20000):
    folder, man, stacks = _load(folder)
    nodes = [n for n in _find_nodes(stacks, obj) if isinstance(n.get('script'), dict)]
    if not nodes:
        return 'no scripted object %r (use "stack", an id or a name)' % obj
    n = nodes[0]
    text = _script_text(folder, n['script'])
    if handler:
        lines = text.splitlines()
        start = None
        for i, l in enumerate(lines):
            m = re.match(r'^\s*(?:private\s+)?(?:on|command|function|getprop|setprop|before|after)\s+(\S+)', l, re.I)
            if m and m.group(1).lower() == handler.lower():
                start = i
                break
        if start is None:
            return 'no handler %r in %s' % (handler, _label(n))
        end = start
        while end < len(lines) and not re.match(r'^\s*end\s+' + re.escape(handler) + r'\b', lines[end], re.I):
            end += 1
        text = '\n'.join('%5d  %s' % (i + 1, lines[i]) for i in range(start, min(end + 1, len(lines))))
    head = '%s%s\n' % (_label(n), ' (%d of them, first shown)' % len(nodes) if len(nodes) > 1 else '')
    if len(text) > maxchars:
        text = text[:maxchars] + '\n... (%d more chars; ask for one handler)' % (len(text) - maxchars)
    return head + text


# ---------------------------------------------------------------------------- command line
def main(argv=None):
    a = sys.argv[1:] if argv is None else argv
    if not a or a[0] in ('-h', '--help'):
        print(__doc__)
        return 0
    cmd, rest = a[0], a[1:]
    try:
        if cmd == 'harvest':
            if not rest:
                print('usage: harvest STACKFILE [OUTFOLDER]', file=sys.stderr)
                return 2
            ok, text = harvest(rest[0], rest[1] if len(rest) > 1 else None)
            print(text)
            return 0 if ok else 1
        fn = {'summary': lambda: summary(rest[0]),
              'handlers': lambda: handlers(rest[0], rest[1] if len(rest) > 1 else None),
              'globals': lambda: globals_(rest[0], rest[1] if len(rest) > 1 else None),
              'custom': lambda: custom(rest[0], *(rest[1:3])),
              'script': lambda: script(rest[0], rest[1], rest[2] if len(rest) > 2 else None)}.get(cmd)
        if fn is None or not rest:
            print(__doc__)
            return 2
        print(fn())
        return 0
    except (ValueError, OSError, IndexError) as e:
        print('xtjson: %s' % e, file=sys.stderr)
        return 1
    except Exception as e:  # NotRunning from lib_mcp
        if type(e).__name__ == 'NotRunning':
            print(e, file=sys.stderr)
            return 2
        raise


if __name__ == '__main__':
    sys.exit(main())
