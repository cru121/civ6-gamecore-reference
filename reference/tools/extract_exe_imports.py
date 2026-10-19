"""DLLs and APIs the Windows engine exe imports, with the number of exe functions that call each (through its import address table slot).
Input : exe_bin/CivilizationVI.exe (a copy of the installed exe; read only), linux_depot/out/scan_win.pkl (function boundaries and references), findings/data/exe_function_index.json
Output: data/exe_imports.json (entities exeimp:<dll>:<api>), data/exe_import_dlls.json."""
import collections, json, os, pickle, re
import pefile
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'tools', 'exe'))
from pelib import undname, FLAGS_SHORT

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ROOT = os.path.abspath(os.path.join(BASE, '..'))
pe = pefile.PE(os.path.join(ROOT, 'exe_bin', 'CivilizationVI.exe'), fast_load=True)
pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_IMPORT']])
base = pe.OPTIONAL_HEADER.ImageBase
scan = pickle.load(open(os.path.join(ROOT, 'linux_depot', 'out', 'scan_win.pkl'), 'rb'))
users = collections.defaultdict(set)
for x in scan:
    for t, k in x[3]:
        users[t].add(x[0])
names = {}
for r in json.load(open(os.path.join(ROOT, 'findings', 'data', 'exe_function_index.json'), encoding='utf8'))['rows']:
    for v in (r[2] or '').split(','):
        if v and r[3] in ('high', 'medium'):
            names.setdefault(int(v, 16), re.sub(r'\(.*$', '', r[0]))

CATS = [('network', r'^(WSA|socket|connect|send|recv|bind|listen|accept|select|gethost|getaddr|freeaddr|inet_|ntoh|hton|closesocket|ioctlsocket|shutdown|WinHttp|Internet|GetAdapters|getsockname|setsockopt|getsockopt|__WSAFD)'),
        ('file system', r'^(CreateFile|ReadFile|WriteFile|FindFirst|FindNext|FindClose|GetFileAttr|SetFileAttr|DeleteFile|MoveFile|CopyFile|CreateDirectory|RemoveDirectory|GetTempPath|GetFullPathName|GetFileSize|SetFilePointer|FlushFileBuffers|ReadDirectoryChanges|GetCurrentDirectory|SetCurrentDirectory|GetModuleFileName|PathFile|Path[A-Z])'),
        ('registry and system information', r'^(Reg[A-Z]|GetVersion|GetSystem|GetNativeSystem|GlobalMemoryStatus|GetComputerName|GetUserName|SHGetKnownFolderPath|SHGet|IsProcessor|GetLogicalProcessor|Setup[A-Z]|GetFileVersion|VerQuery)'),
        ('processes, threads and modules', r'^(CreateProcess|CreateThread|ExitProcess|TerminateProcess|OpenProcess|GetCurrentProcess|GetCurrentThread|LoadLibrary|GetProcAddress|FreeLibrary|ShellExecute|WaitForSingle|WaitForMultiple|CreateEvent|CreateMutex|Sleep|SetThread|GetModuleHandle|TlsAlloc|FlsAlloc|InitializeCriticalSection|EnterCriticalSection)'),
        ('debugging and crash handling', r'^(SymInitialize|Sym[A-Z]|StackWalk|MiniDump|UnhandledException|SetUnhandledExceptionFilter|IsDebuggerPresent|OutputDebugString|RaiseException|RtlCaptureContext|RtlLookupFunctionEntry|RtlVirtualUnwind|CaptureStackBackTrace|UnDecorate)'),
        ('windowing and input', r'^(CreateWindow|RegisterClass|DefWindowProc|GetMessage|PeekMessage|DispatchMessage|TranslateMessage|SetWindow|GetWindow|ShowWindow|ImmGet|ImmSet|ImmAssociate|GetKeyboard|GetAsyncKeyState|GetCursor|SetCursor|ClipCursor|MessageBox|GetRawInput|RegisterRawInput|SendInput|GetClipboard|SetClipboard|OpenClipboard|Enum[A-Z]|MonitorFrom|GetMonitorInfo|ChangeDisplay)')]
CAT_RX = [(n, re.compile(rx)) for n, rx in CATS]
ents = []
dlls = []
for d in pe.DIRECTORY_ENTRY_IMPORT:
    dn = d.dll.decode()
    cnt = 0
    for imp in d.imports:
        nm = imp.name.decode() if imp.name else 'ordinal %d' % imp.ordinal
        iat = imp.address - base
        fs = sorted(users.get(iat, ()))
        cat = next((c for c, rx in CAT_RX if rx.search(nm)), 'other')
        pretty = undname(nm, 0x2 | 0x8) if nm.startswith('?') else nm
        ents.append({'id': 'exeimp:%s:%s' % (dn.lower(), nm), 'dll': dn, 'api': nm, 'display': pretty, 'category': cat, 'iat_rva': '0x%x' % iat, 'caller_count': len(fs),
                     'callers': [{'rva': '0x%x' % f, 'name': names.get(f)} for f in fs[:3]], 'availability': 'exe', 'status': 'verified',
                     'evidence': [{'kind': 'exe-disassembly', 'note': 'entry of the PE import table; callers counted from code references to its import address table slot'}]})
        cnt += 1
    dlls.append({'dll': dn, 'imports': cnt, 'called': sum(1 for e in ents if e['dll'] == dn and e['caller_count']), 'calls': sum(e['caller_count'] for e in ents if e['dll'] == dn)})
json.dump(ents, open(os.path.join(BASE, 'data', 'exe_imports.json'), 'w', encoding='utf8'), indent=1, ensure_ascii=False)
json.dump(dlls, open(os.path.join(BASE, 'data', 'exe_import_dlls.json'), 'w', encoding='utf8'), indent=1, ensure_ascii=False)
print(len(ents), 'imports from', len(dlls), 'dlls;', collections.Counter(e['category'] for e in ents).most_common())
