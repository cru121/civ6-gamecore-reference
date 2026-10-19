"""Developer tools and crash reports of the exe: the FireTuner (AppTuner2) command protocol, the AssetCloud hot-load listener, the Automation hooks, the bug submission header and the exception names.
Input : linux_depot/out/exetrace/tools_decomp.txt (DecompList.java on ghi-exe: Tuner ProcessInput 0x4f5bf0, AssetCloud ProcessInput 0x4ef4f0, bug header 0x705e70), the exe image (command names that are
        constants, read at the addresses the decompile shows), linux_depot/out/strmaps.pkl (handler strings), findings/data/exe_function_index.json (handler names)
Output: data/exe_devtools.json (entities exedev:<kind>:<name>)."""
import collections, json, os, pickle, re, sys

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ROOT = os.path.abspath(os.path.join(BASE, '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'exe'))
from pelib import Img

im = Img()


def dat(a):
    return im.read(a, 24).split(b'\0')[0].decode('ascii')


ws, ls, wm, lm = pickle.load(open(os.path.join(ROOT, 'linux_depot', 'out', 'strmaps.pkl'), 'rb'))
names = {}
for r in json.load(open(os.path.join(ROOT, 'findings', 'data', 'exe_function_index.json'), encoding='utf8'))['rows']:
    for v in (r[2] or '').split(','):
        if v and r[3] in ('high', 'medium'):
            names.setdefault(int(v, 16), re.sub(r'\(.*$', '', r[0]))
strs = collections.defaultdict(set)
for a, s in ws.items():
    s = s.decode('latin1') if isinstance(s, bytes) else s
    for f in wm.get(a, ()):
        if 'BuildAgent' not in s and not s.startswith('[%04d'):
            strs[f].add(s)

text = open(os.path.join(ROOT, 'linux_depot', 'out', 'exetrace', 'tools_decomp.txt'), encoding='utf8').read().replace('\r', '')
ch = {c.split('\t')[0].strip().lower(): c for c in re.split(r'\n?@@@ ', text)[1:]}

# FireTuner commands: the dispatch of Tuner::AppTuner2::Listener::ProcessInput (0x4f5bf0): "COMMAND:args", per-state commands "<state index>:COMMAND:args".
APP = [('DAT_140feb824', 0x4f6d10), ('DAT_140feb6c0', 0x4f13c0), ('CLOSE', 0x4efee0), ('DAT_140feb828', 0x4f4e00), ('STRACKERS', 0x4f43c0), ('START_TRACKER', 0x4f4380), ('STOP_TRACKER', 0x4f4420),
       ('DAT_140fc0914', 0x4f2650), ('HOTLOAD', None)]
STATE = [('DAT_140feb868', 0x4f6b70), ('DAT_140feb86c', 0x4f1ee0), ('HELPT', 0x4f5070), ('DAT_140feb87c', 0x4f3dc0), ('DAT_140feb880', 0x4f3890), ('KILLQRY', 0x4f1750), ('TABLE', 0x4f4960),
         ('CUSTOM_TABLE', 0x4f1d10), ('CUSTOM_TABLE_SEL', 0x4f2cd0), ('DAT_140feb8bc', 0x4f2f10), ('LISTSEL', 0x4f2cd0), ('MLIST', 0x4f32f0)]
MEANING = {
    'LSQ': 'handler not named; the command word suggests a query for the list of Lua states (guess)', 'APP': 'handler is `RegisterTree` in the function map (low confidence): registers the value tree of the tuner and then sends application information (guess)',
    'CLOSE': 'close the tuner connection', 'TREE': 'request a tree of values (reply lines `D<name> = <value>`)', 'STRACKERS': 'list the statistic trackers (reply `TrackerList`)',
    'START_TRACKER': 'start a statistic tracker (name; handler not named)', 'STOP_TRACKER': 'stop a statistic tracker (name; handler not named)', 'LOAD': 'handler not named; the word suggests a load request (guess)',
    'HOTLOAD': 'reload assets while the game runs: `HOTLOAD:ARTDEF:<name>`, `HOTLOAD:UI:<name>` or `HOTLOAD:<other>:<name>` (blueprint reload)',
    'CMD': 'run a console command in the Lua state (`RunConsoleCommand`; error `ERR:Invalid Lua State`)', 'HELP': 'help for an object or table: `BaseType`, `ExposedMembers`, `__index` lookups',
    'HELPT': 'help for a table / array (`HandleArrayHelpRequest`, reply `%s (%s)`)', 'VAL': 'set a value (`ERR:SET:`, `ERR:SET:Bad lua state`, `ERR:No Query Found`)', 'QRY': 'run a query function (`ERR:Bad lua state`)',
    'KILLQRY': 'cancel a running query', 'TABLE': 'list the contents of a Lua table (marks the metatable as `* Metatable *`)', 'CUSTOM_TABLE': 'populate a custom table (`Populate Table Error`)',
    'CUSTOM_TABLE_SEL': 'selection in a custom table (`OnSelection Error`)', 'LIST': 'populate a list (`Populate List Success`, `Populate List Success;Selected=%d`, `Populate List Error`)',
    'LISTSEL': 'selection in a list (same handler as the custom table selection)', 'MLIST': 'populate a multiselect list (`Populate List Success`)'}
ents = []
for scope, lst in (('application', APP), ('lua-state', STATE)):
    for k, h in lst:
        nm = dat(int(k[4:], 16) - 0x140000000) if k.startswith('DAT_') else k
        hn = names.get(h) if h else None
        rep = sorted(strs.get(h, [])) if h else []
        ents.append({'id': 'exedev:tuner-command:%s' % nm, 'kind': 'tuner-command', 'name': nm, 'scope': scope, 'handler': hn or ('0x%x' % h if h else 'ProcessInput (kind dispatch)'), 'handler_rva': '0x%x' % h if h else '0x4f5bf0',
                     'strings': rep[:8], 'meaning': MEANING.get(nm, ''), 'availability': 'exe', 'status': 'verified' if hn else 'inferred',
                     'evidence': [{'kind': 'exe-disassembly', 'note': 'compared in the dispatch of Tuner::AppTuner2::Listener::ProcessInput (0x4f5bf0), decompiled; handler names from the Linux function map; meaning inferred from handler names and strings'}]})
# the other Tuner listener: AssetCloud (hot loading of assets by an external tool)
for nm, mean in (('CLOSE', 'close the asset cloud connection (log: "Received close request.")'), ('HOTLOAD', 'hot load a file (log: "Received Hotload request: \'%s\'." then "HotLoad complete."); queue entries are `ARTDEF:` and `DEPENDENCY:` (log: "Adding ArtDef/BLP \'%s\' to the hot load queue")')):
    ents.append({'id': 'exedev:assetcloud-command:%s' % nm, 'kind': 'assetcloud-command', 'name': nm, 'scope': 'assetcloud', 'handler': 'AssetCloud::Listener::ProcessInput', 'handler_rva': '0x4ef4f0',
                 'strings': [], 'meaning': mean, 'availability': 'exe', 'status': 'verified',
                 'evidence': [{'kind': 'exe-string', 'note': 'command strings compared in AssetCloud::Listener::ProcessInput (0x4ef4f0); log file AssetCloudTuner.log'}]})
# bug submission header: element order of GenerateHeaderInSubmissionFolder (0x705e70)
HEADER = [('GUID', ''), ('Application', ''), ('SubmissionType', ''), ('Host', ''), ('Time', 'formatted %04d-%02d-%02d %02d:%02d:%02d'), ('File', ''), ('Line', ''), ('Message', ''), ('Callstack', ''), ('Catalog', ''),
          ('Log', 'child File, MD5'), ('Dump', 'child File, MD5'), ('Attachments', 'child File, MD5'), ('Exception', 'children Message, StackTrace, ModuleInfo'),
          ('ModuleInfo', 'attributes file, baseAddr, size, guid1, guid2, guid3, guid4, age, pdbPath'), ('Version', 'children Major, Minor, Rev, Build, Changelist'), ('Session', 'children Hash, Time')]
body = ch['0x705e70']
seen = []
for m in re.finditer(r'"([^"]*)"', body):
    t = m.group(1)
    if 'BuildAgent' not in t and not t.startswith('[%04d') and t not in seen:
        seen.append(t)
for k, (n, d) in enumerate(HEADER):
    ents.append({'id': 'exedev:bug-header:%s' % n, 'kind': 'bug-header', 'name': n, 'scope': 'bug submission header', 'handler': 'AppHost::BugSubmissionPackager::GenerateHeaderInSubmissionFolder', 'handler_rva': '0x705e70',
                 'strings': [d] if d else [], 'meaning': 'element %d of the header written to the bug submission folder%s' % (k + 1, (' (' + d + ')') if d else ''),
                 'availability': 'exe', 'status': 'verified' if n in seen or n.lower() in seen else 'inferred',
                 'evidence': [{'kind': 'exe-string', 'note': 'element/attribute name string in GenerateHeaderInSubmissionFolder (0x705e70); the grouping into children is inferred from the order of the strings'}]})
# exception names (FDebugHelperNS::GetExceptionDescription 0x986d20) with the Windows exception code of each name
CODES = {'EXCEPTION_ACCESS_VIOLATION': 0xC0000005, 'EXCEPTION_ARRAY_BOUNDS_EXCEEDED': 0xC000008C, 'EXCEPTION_BREAKPOINT': 0x80000003, 'EXCEPTION_DATATYPE_MISALIGNMENT': 0x80000002,
         'EXCEPTION_FLT_DENORMAL_OPERAND': 0xC000008D, 'EXCEPTION_FLT_DIVIDE_BY_ZERO': 0xC000008E, 'EXCEPTION_FLT_INEXACT_RESULT': 0xC000008F, 'EXCEPTION_FLT_INVALID_OPERATION': 0xC0000090,
         'EXCEPTION_FLT_OVERFLOW': 0xC0000091, 'EXCEPTION_FLT_STACK_CHECK': 0xC0000092, 'EXCEPTION_FLT_UNDERFLOW': 0xC0000093, 'EXCEPTION_GUARD_PAGE': 0x80000001, 'EXCEPTION_ILLEGAL_INSTRUCTION': 0xC000001D,
         'EXCEPTION_IN_PAGE_ERROR': 0xC0000006, 'EXCEPTION_INT_DIVIDE_BY_ZERO': 0xC0000094, 'EXCEPTION_INT_OVERFLOW': 0xC0000095, 'EXCEPTION_INVALID_DISPOSITION': 0xC0000026, 'EXCEPTION_INVALID_HANDLE': 0xC0000008,
         'EXCEPTION_NONCONTINUABLE_EXCEPTION': 0xC0000025, 'EXCEPTION_PRIV_INSTRUCTION': 0xC0000096, 'EXCEPTION_SINGLE_STEP': 0x80000004, 'EXCEPTION_STACK_OVERFLOW': 0xC00000FD}
gx = [f for f, n in names.items() if n == 'FDebugHelperNS::GetExceptionDescription']
exc = sorted(s for f in gx for s in strs.get(f, ()) if s.startswith('EXCEPTION_'))
for e in exc:
    ents.append({'id': 'exedev:exception:%s' % e, 'kind': 'exception', 'name': e, 'scope': 'crash handler', 'handler': 'FDebugHelperNS::GetExceptionDescription', 'handler_rva': '0x986d20',
                 'strings': [('0x%08X' % CODES[e]) if e in CODES else ''], 'meaning': 'name shown in the crash dialog and report for the Windows exception code%s' % ((' 0x%08X' % CODES[e]) if e in CODES else ''),
                 'availability': 'exe', 'status': 'verified', 'evidence': [{'kind': 'exe-string', 'note': 'exception name string in FDebugHelperNS::GetExceptionDescription (0x986d20); code values are the documented Windows constants'}]})
# automation hooks
for n, d in (('AutomationAppInitComplete', 'raised when the app finished initialising (Automation::Manager::OnAppInitComplete)'), ('AutomationMainMenuStarted', 'raised when the main menu started'),
             ('AutomationPostGameInitialization', 'raised after game initialisation (Automation::Manager::PostGameInitialization)'), ('$(Automation)', 'file name tag replaced by the automation folder in output file names'),
             ('$(ID)', 'file name tag replaced by the run id'), ('Automation_%04d_%02d_%02d__%02d_%02d_%02d', 'default automation output name pattern (date and time)')):
    ents.append({'id': 'exedev:automation:%s' % n, 'kind': 'automation', 'name': n, 'scope': 'automation', 'handler': 'App::Automation::Manager', 'handler_rva': '', 'strings': [], 'meaning': d,
                 'availability': 'exe', 'status': 'verified', 'evidence': [{'kind': 'exe-string', 'note': 'string literal of App::Automation::Manager functions'}]})
json.dump(ents, open(os.path.join(BASE, 'data', 'exe_devtools.json'), 'w', encoding='utf8'), indent=1, ensure_ascii=False)
print(len(ents), dict(collections.Counter(e['kind'] for e in ents)))
print([e['name'] for e in ents if e['kind'] == 'tuner-command'])
print(len(exc), 'exception names;', [e for e in exc if e not in CODES])
print([e['name'] for e in ents if e['kind'] == 'bug-header' and e['status'] == 'inferred'])
