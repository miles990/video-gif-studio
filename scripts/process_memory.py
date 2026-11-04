"""Read process-tree RSS without installing dependencies during a benchmark."""
import os

try:
    import psutil
except ImportError:
    psutil = None


def tree_memory(pid):
    """Return (RSS sum, peak working-set sum) for a parent and live descendants.

    Windows fallback uses Toolhelp32Snapshot + GetProcessMemoryInfo. This is the
    same working-set counter exposed by psutil, sampled rather than inferred.
    Per-process peaks need not be simultaneous; their sum is conservative.
    """
    if psutil is not None:
        try:
            parent=psutil.Process(pid);children=[parent]+parent.children(recursive=True)
        except psutil.Error:return 0,0
        rss=peak=0
        for child in children:
            try:
                info=child.memory_info();rss+=info.rss;peak+=getattr(info,'peak_wset',info.rss)
            except psutil.Error:pass
        return rss,peak
    if os.name != 'nt':
        raise RuntimeError('Install psutil to measure process-tree RSS on this OS')
    import ctypes as c
    from ctypes import wintypes as w
    class Process(c.Structure):
        _fields_=[('size',w.DWORD),('usage',w.DWORD),('pid',w.DWORD),('heap',c.c_size_t),
            ('module',w.DWORD),('threads',w.DWORD),('parent',w.DWORD),('priority',w.LONG),
            ('flags',w.DWORD),('exe',w.WCHAR*260)]
    class Memory(c.Structure):
        _fields_=[('cb',w.DWORD),('faults',w.DWORD),('peak',c.c_size_t),('rss',c.c_size_t),
            ('quota_peak_paged',c.c_size_t),('quota_paged',c.c_size_t),
            ('quota_peak_nonpaged',c.c_size_t),('quota_nonpaged',c.c_size_t),
            ('pagefile',c.c_size_t),('peak_pagefile',c.c_size_t)]
    kernel=c.WinDLL('kernel32',use_last_error=True);api=c.WinDLL('psapi',use_last_error=True)
    kernel.CreateToolhelp32Snapshot.argtypes=[w.DWORD,w.DWORD];kernel.CreateToolhelp32Snapshot.restype=w.HANDLE
    kernel.Process32FirstW.argtypes=[w.HANDLE,c.POINTER(Process)]
    kernel.Process32NextW.argtypes=[w.HANDLE,c.POINTER(Process)]
    kernel.OpenProcess.argtypes=[w.DWORD,w.BOOL,w.DWORD];kernel.OpenProcess.restype=w.HANDLE
    kernel.CloseHandle.argtypes=[w.HANDLE]
    api.GetProcessMemoryInfo.argtypes=[w.HANDLE,c.POINTER(Memory),w.DWORD]
    snapshot=kernel.CreateToolhelp32Snapshot(2,0);entry=Process();entry.size=c.sizeof(entry)
    parents={}
    try:
        valid=kernel.Process32FirstW(snapshot,c.byref(entry))
        while valid:
            parents[entry.pid]=entry.parent
            valid=kernel.Process32NextW(snapshot,c.byref(entry))
    finally:kernel.CloseHandle(snapshot)
    wanted={pid}
    while True:
        more={child for child,parent in parents.items() if parent in wanted}-wanted
        if not more:break
        wanted.update(more)
    rss=peak=0
    for child in wanted:
        handle=kernel.OpenProcess(0x0400|0x0010,False,child)
        if not handle:continue
        try:
            info=Memory();info.cb=c.sizeof(info)
            if api.GetProcessMemoryInfo(handle,c.byref(info),info.cb):rss+=info.rss;peak+=info.peak
        finally:kernel.CloseHandle(handle)
    return rss,peak
