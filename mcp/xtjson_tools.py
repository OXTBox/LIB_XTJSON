"""XTJSON tool pack for LIB_MCP's MCP server (LM Studio, Claude Desktop, Claude Code).

    python3 ~/projects/LIB_MCP/python/lib_mcp/mcp_server.py --tools ~/projects/LIB_XTJSON/mcp/xtjson_tools.py

Adds: xtjson_harvest (stack file -> XTJSON folder; needs the LIB_MCP standalone or IDE),
and read-only questions about a harvest that need no LiveCode: xtjson_summary,
xtjson_handlers, xtjson_globals, xtjson_custom, xtjson_script. All answers are plain text,
so small models never have to read the raw JSON. The work is done by
../python/xtjson_harvest.py (also a command line, and `lcmcp harvest`).
"""
import os, sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'python'))
import xtjson_harvest as xh  # noqa: E402

S = {'type': 'string'}
HV = dict(S, description='harvest folder path, or its name under ~/projects/XTJSON')


def schema(props, required):
    return {'type': 'object', 'properties': props, 'required': required}


def t_harvest(a):
    from lib_mcp.client import Client, NotRunning, IDE_PORT
    try:
        c = Client.standalone()
    except NotRunning:
        c = Client(IDE_PORT)
    ok, text = xh.harvest(a['stack_file'], a.get('out_folder') or None, client=c)
    return text if ok else 'HARVEST DID NOT COMPLETE\n' + text


TOOLS = [
    ('xtjson_harvest', t_harvest,
     'Export a LiveCode/xTalk stack file (.livecode) to an XTJSON folder: stack -> cards -> controls as JSON, '
     'every script as its own file, images, custom properties. The stack is read only; its own handlers do '
     'not run. Returns a summary. Default output: ~/projects/XTJSON/<file name>.',
     schema({'stack_file': dict(S, description='path of the .livecode file (WSL, Windows or \\\\wsl$ path)'),
             'out_folder': dict(S, description='optional output folder')}, ['stack_file'])),
    ('xtjson_summary', lambda a: xh.summary(a['harvest']),
     'Overview of a harvest: counts, biggest scripts, custom property sets. Start here.',
     schema({'harvest': HV}, ['harvest'])),
    ('xtjson_handlers', lambda a: xh.handlers(a['harvest'], a.get('filter')),
     'List handlers (object, line, type, name, params). Optional filter text, e.g. "turn." or "mouseUp".',
     schema({'harvest': HV, 'filter': S}, ['harvest'])),
    ('xtjson_globals', lambda a: xh.globals_(a['harvest'], a.get('filter')),
     'List global variables declared in all scripts, with how many objects use them and their comments.',
     schema({'harvest': HV, 'filter': S}, ['harvest'])),
    ('xtjson_custom', lambda a: xh.custom(a['harvest'], a.get('set'), a.get('key'), a.get('object')),
     'Read custom properties. No set: list the sets. With set: all its keys and values. With key: one value. '
     'object is "stack" (default), an object id or a name.',
     schema({'harvest': HV, 'set': S, 'key': S, 'object': S}, ['harvest'])),
    ('xtjson_script', lambda a: xh.script(a['harvest'], a['object'], a.get('handler')),
     'Read the script of an object ("stack", an id or a name), or just one handler of it with line numbers.',
     schema({'harvest': HV, 'object': S, 'handler': S}, ['harvest', 'object'])),
]
