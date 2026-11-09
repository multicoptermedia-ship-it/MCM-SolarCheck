"""Capture one owned OpenSfM inventory worker's native shutdown stack on Windows.

Uses existing MSVC/SDK and Win32 Debug APIs; no installation, dumps, photos,
symbols from the network, engine changes or forced-success exit handling.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import sys
import tempfile


GPU_HASH = 'bcdd2f249d6f37855ea5bdcbb8a761d03d121fec2ff1c947c525d0b44c693b6f'
ROOT = r'E:\SolarCheck-OpenSfM'

# StackWalk64 is Microsoft's existing x64 unwind implementation. No custom
# unwinder, symbol server, memory dump or engine patch is introduced here.
SOURCE = r'''
#define NOMINMAX
#include <windows.h>
#include <dbghelp.h>
#include <psapi.h>
#include <cstdio>
#include <string>
#include <vector>
#include <cctype>
#include <algorithm>

#ifndef _M_X64
#error x64 required
#endif

struct Frame { std::string module; DWORD64 offset; bool known; };
struct Module { DWORD64 base; DWORD size; std::string name; };

static std::wstring quote(const std::wstring& arg) {
    std::wstring out = L"\"";
    size_t slashes = 0;
    for (wchar_t c : arg) {
        if (c == L'\\') { ++slashes; continue; }
        if (c == L'\"') { out.append(slashes * 2 + 1, L'\\'); out += c; }
        else { out.append(slashes, L'\\'); out += c; }
        slashes = 0;
    }
    out.append(slashes * 2, L'\\');
    return out + L"\"";
}

static std::string safe_name(const char* name) {
    std::string result(name);
    if (result.empty() || result.size() > 96) return "redacted_module";
    for (unsigned char c : result)
        if (!(c < 128 && (std::isalnum(c) || c == '.' || c == '_' || c == '-' || c == '+')))
            return "redacted_module";
    return result;
}

static std::vector<Module> modules(HANDLE process) {
    HMODULE entries[2048];
    DWORD bytes = 0;
    std::vector<Module> result;
    if (!EnumProcessModulesEx(process, entries, sizeof(entries), &bytes, LIST_MODULES_64BIT))
        return result;
    size_t count = (std::min)(static_cast<size_t>(bytes / sizeof(HMODULE)), size_t(2048));
    for (size_t i = 0; i < count; ++i) {
        MODULEINFO info{};
        char name[256]{};
        if (GetModuleInformation(process, entries[i], &info, sizeof(info)) &&
            GetModuleBaseNameA(process, entries[i], name, sizeof(name)))
            result.push_back({reinterpret_cast<DWORD64>(info.lpBaseOfDll), info.SizeOfImage, safe_name(name)});
    }
    return result;
}

static Frame locate(DWORD64 pc, const std::vector<Module>& list) {
    for (const auto& mod : list)
        if (pc >= mod.base && pc - mod.base < mod.size)
            return {mod.name, pc - mod.base, true};
    return {"unknown_module", 0, false};
}

static std::vector<Frame> capture(HANDLE process, HANDLE thread, const wchar_t* empty_symbols) {
    CONTEXT context{};
    context.ContextFlags = CONTEXT_FULL;
    if (!GetThreadContext(thread, &context)) return {};
    auto list = modules(process);
    std::vector<Frame> result{locate(context.Rip, list)};
    // Ignore environment symbol paths AND embedded PDB references. We only
    // need PE/x64 unwind tables; the explicit search directory is owned/empty.
    SymSetOptions(SYMOPT_DEFERRED_LOADS | SYMOPT_FAIL_CRITICAL_ERRORS |
        SYMOPT_NO_PROMPTS | SYMOPT_IGNORE_NT_SYMPATH | SYMOPT_IGNORE_CVREC |
        SYMOPT_DISABLE_SYMSRV_AUTODETECT | SYMOPT_SECURE);
    if (!SymInitializeW(process, empty_symbols, TRUE)) return result;
    STACKFRAME64 frame{};
    frame.AddrPC.Offset = context.Rip;
    frame.AddrPC.Mode = AddrModeFlat;
    frame.AddrStack.Offset = context.Rsp;
    frame.AddrStack.Mode = AddrModeFlat;
    frame.AddrFrame.Offset = context.Rbp;
    frame.AddrFrame.Mode = AddrModeFlat;
    DWORD64 previous_pc = context.Rip, previous_sp = context.Rsp;
    for (int i = 0; i < 31; ++i) {
        if (!StackWalk64(IMAGE_FILE_MACHINE_AMD64, process, thread, &frame, &context,
            nullptr, SymFunctionTableAccess64, SymGetModuleBase64, nullptr) || !frame.AddrPC.Offset)
            break;
        if (frame.AddrPC.Offset == previous_pc && frame.AddrStack.Offset == previous_sp) break;
        // StackWalk's first result may describe the current instruction.
        if (frame.AddrPC.Offset != previous_pc)
            result.push_back(locate(frame.AddrPC.Offset, list));
        previous_pc = frame.AddrPC.Offset;
        previous_sp = frame.AddrStack.Offset;
    }
    SymCleanup(process);
    return result;
}

int wmain(int argc, wchar_t** argv) {
    SetErrorMode(SEM_FAILCRITICALERRORS | SEM_NOGPFAULTERRORBOX | SEM_NOOPENFILEERRORBOX);
    if (argc == 2 && std::wstring(argv[1]) == L"--av-child") {
        RaiseException(EXCEPTION_ACCESS_VIOLATION, EXCEPTION_NONCONTINUABLE, 0, nullptr);
        return 99;
    }
    if (argc == 2 && std::wstring(argv[1]) == L"--clean-child") return 0;
    if (argc == 2 && std::wstring(argv[1]) == L"--wait-child") { Sleep(10000); return 0; }
    bool synthetic = argc == 3 && (std::wstring(argv[1]) == L"--synthetic-av" ||
        std::wstring(argv[1]) == L"--synthetic-clean" || std::wstring(argv[1]) == L"--synthetic-timeout");
    bool inventory = argc == 5 && std::wstring(argv[1]) == L"--inventory";
    if (!synthetic && !inventory) return 2;
    const wchar_t* symbols = argv[synthetic ? 2 : 4];
    std::wstring application, command;
    DWORD limit = 30000;
    if (synthetic) {
        wchar_t self[32768];
        DWORD size = GetModuleFileNameW(nullptr, self, 32768);
        if (!size || size >= 32768) return 2;
        application.assign(self, size);
        std::wstring mode(argv[1]);
        command = quote(application) + (mode == L"--synthetic-av" ? L" --av-child" :
            mode == L"--synthetic-clean" ? L" --clean-child" : L" --wait-child");
        if (mode == L"--synthetic-timeout") limit = 200;
    } else {
        application = argv[2];
        command = quote(application) + L" -I " + quote(argv[3]) +
            L" --worker inventory --system-opencl --cli-imports";
    }
    // Child output never enters the console or a raw log. Only our filtered
    // stack report is emitted; do not inherit the parent console handles.
    SECURITY_ATTRIBUTES security{sizeof(SECURITY_ATTRIBUTES), nullptr, TRUE};
    HANDLE nullfile = CreateFileW(L"NUL", GENERIC_READ | GENERIC_WRITE,
        FILE_SHARE_READ | FILE_SHARE_WRITE, &security, OPEN_EXISTING, 0, nullptr);
    if (nullfile == INVALID_HANDLE_VALUE) return 2;
    STARTUPINFOW startup{};
    startup.cb = sizeof(startup);
    startup.dwFlags = STARTF_USESTDHANDLES;
    startup.hStdInput = startup.hStdOutput = startup.hStdError = nullfile;
    PROCESS_INFORMATION process{};
    BOOL started = CreateProcessW(application.c_str(), command.data(), nullptr, nullptr, TRUE,
        DEBUG_ONLY_THIS_PROCESS | CREATE_NO_WINDOW, nullptr, nullptr, &startup, &process);
    CloseHandle(nullfile);
    if (!started) { std::puts("{\"status\":\"launch_failed\"}"); return 1; }
    DebugSetProcessKillOnExit(TRUE);
    ULONGLONG deadline = GetTickCount64() + limit;
    bool captured = false, exited = false, timed_out = false, initial_break = true;
    DWORD exit_code = STILL_ACTIVE, exception = 0;
    std::vector<Frame> frames;
    while (!exited && GetTickCount64() < deadline) {
        DEBUG_EVENT event{};
        if (!WaitForDebugEvent(&event, 100)) continue;
        DWORD continuation = DBG_CONTINUE;
        if (event.dwDebugEventCode == CREATE_PROCESS_DEBUG_EVENT) {
            if (event.u.CreateProcessInfo.hFile) CloseHandle(event.u.CreateProcessInfo.hFile);
            // The debug event owns separate handles from PROCESS_INFORMATION.
            if (event.u.CreateProcessInfo.hProcess != process.hProcess) CloseHandle(event.u.CreateProcessInfo.hProcess);
            if (event.u.CreateProcessInfo.hThread != process.hThread) CloseHandle(event.u.CreateProcessInfo.hThread);
        } else if (event.dwDebugEventCode == CREATE_THREAD_DEBUG_EVENT) {
            CloseHandle(event.u.CreateThread.hThread);
        } else if (event.dwDebugEventCode == LOAD_DLL_DEBUG_EVENT) {
            if (event.u.LoadDll.hFile) CloseHandle(event.u.LoadDll.hFile);
        } else if (event.dwDebugEventCode == EXCEPTION_DEBUG_EVENT) {
            auto& info = event.u.Exception;
            DWORD code = info.ExceptionRecord.ExceptionCode;
            continuation = DBG_EXCEPTION_NOT_HANDLED;
            if (initial_break && code == EXCEPTION_BREAKPOINT && info.dwFirstChance) {
                initial_break = false;
                continuation = DBG_CONTINUE;
            } else if (!info.dwFirstChance && !captured) {
                captured = true;
                exception = code;
                HANDLE thread = OpenThread(THREAD_GET_CONTEXT | THREAD_QUERY_INFORMATION, FALSE, event.dwThreadId);
                if (thread) { frames = capture(process.hProcess, thread, symbols); CloseHandle(thread); }
            }
        } else if (event.dwDebugEventCode == EXIT_PROCESS_DEBUG_EVENT) {
            exited = true;
            exit_code = event.u.ExitProcess.dwExitCode;
        }
        ContinueDebugEvent(event.dwProcessId, event.dwThreadId, continuation);
    }
    if (!exited) {
        timed_out = true;
        // Only the process we launched. No global taskkill or debugger attach.
        TerminateProcess(process.hProcess, WAIT_TIMEOUT);
        // Drain events to allow a debuggee to terminate while under debug.
        ULONGLONG drain = GetTickCount64() + 3000;
        while (GetTickCount64() < drain) {
            DEBUG_EVENT event{};
            if (!WaitForDebugEvent(&event, 100)) continue;
            ContinueDebugEvent(event.dwProcessId, event.dwThreadId, DBG_CONTINUE);
            if (event.dwDebugEventCode == EXIT_PROCESS_DEBUG_EVENT) break;
        }
        WaitForSingleObject(process.hProcess, 1000);
        GetExitCodeProcess(process.hProcess, &exit_code);
    }
    CloseHandle(process.hThread);
    CloseHandle(process.hProcess);
    std::printf("{\"status\":\"%s\",\"target_exit_code\":%lu,\"target_exit_code_hex\":\"0x%08lX\","
        "\"exception_code_hex\":\"0x%08lX\",\"frames\":[",
        timed_out ? "timeout" : captured ? "captured" : exit_code ? "exit_without_stack" : "clean_exit",
        exit_code, exit_code, exception);
    for (size_t i = 0; i < frames.size(); ++i) {
        if (i) std::putchar(',');
        std::printf("{\"module\":\"%s\"", frames[i].module.c_str());
        if (frames[i].known) std::printf(",\"offset\":\"0x%llX\"", frames[i].offset);
        std::putchar('}');
    }
    std::puts("]}");
    return captured && !timed_out ? 0 : 1;
}
'''


def load_buildtools():
    path = Path(__file__).resolve().with_name('MCM_SolarCheck_BUILDTOOLS_PRUEFUNG.py')
    spec = importlib.util.spec_from_file_location('solarcheck_stack_buildtools', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def compile_helper(work, sdk):
    candidate = sdk.find_vs2022()
    if not candidate:
        return {'status': 'vs2022_cpp_not_found'}
    vcvars = Path(candidate['installationPath']) / 'VC' / 'Auxiliary' / 'Build' / 'vcvars64.bat'
    if not vcvars.is_file() or not sdk.batch_path_supported(vcvars):
        return {'status': 'setup_path_unsupported'}
    batch = ('@echo off\r\nsetlocal\r\n'
             f'call "{vcvars}" > activate.log 2>&1\r\n'
             'if errorlevel 1 exit /b 11\r\n'
             'cd /d "%~dp0"\r\n'
             'cl.exe /nologo /std:c++17 /EHsc /MT /Fostack.obj /Festack.exe '
             'stack.cpp /link dbghelp.lib psapi.lib > build.log 2>&1\r\n'
             'if errorlevel 1 exit /b 12\r\nexit /b 0\r\n')
    (work / 'stack.cpp').write_text(SOURCE, encoding='ascii')
    (work / 'check.cmd').write_bytes(batch.encode('ascii'))
    env = os.environ.copy()
    env.update(TEMP=str(work / 'temp'), TMP=str(work / 'temp'), VSCMD_SKIP_SENDTELEMETRY='1')
    for name in ('CL', '_CL_', 'LINK', '_LINK_'):
        env.pop(name, None)
    code = sdk.run_batch(work, env)
    if code != 0:
        return {'status': 'compiler_timed_out' if code is None else 'compile_failed',
                'compiler_codes': sdk.error_codes(work)}
    if not sdk.is_x64_executable(work / 'stack.exe'):
        return {'status': 'helper_not_x64'}
    return {'status': 'compiled'}


def run_capture(work, python=None, gpu_script=None, synthetic=None):
    command = [str(work / 'stack.exe')]
    if synthetic:
        command += ['--synthetic-' + synthetic, str(work / 'symbols')]
    else:
        command += ['--inventory', str(python), str(gpu_script), str(work / 'symbols')]
    env = os.environ.copy()
    for key in list(env):
        if key.upper() in ('_NT_SYMBOL_PATH', '_NT_ALT_SYMBOL_PATH'):
            env.pop(key)
    env.update(TEMP=str(work / 'temp'), TMP=str(work / 'temp'),
               MPLCONFIGDIR=str(work / 'matplotlib'), PROJ_NETWORK='OFF')
    try:
        result = subprocess.run(command, cwd=work, env=env, capture_output=True,
                                timeout=40, check=False,
                                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    except subprocess.TimeoutExpired:
        # DebugSetProcessKillOnExit closes only this helper's debuggee on exit.
        return {'status': 'debugger_timeout'}
    return filtered_report(result.stdout, result.returncode)


def filtered_report(stdout, helper_exit):
    try:
        raw = json.loads(stdout)
        status = raw['status']
        if status not in ('captured', 'timeout', 'clean_exit', 'exit_without_stack', 'launch_failed'):
            raise ValueError('status')
        if status == 'launch_failed':
            return {'status': status}
        code = raw['target_exit_code']
        if type(code) is not int or not 0 <= code <= 0xffffffff:
            raise ValueError('exit')
        exception = raw['exception_code_hex']
        if not re.fullmatch(r'0x[0-9A-F]{8}', exception):
            raise ValueError('exception')
        frames = raw['frames']
        if not isinstance(frames, list) or len(frames) > 32:
            raise ValueError('frames')
        safe = []
        for frame in frames:
            name = frame['module']
            if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9_.+\-]{1,96}', name):
                raise ValueError('module')
            row = {'module': name}
            if 'offset' in frame:
                offset = frame['offset']
                if not isinstance(offset, str) or not re.fullmatch(r'0x[0-9A-F]{1,8}', offset):
                    raise ValueError('offset')
                row['offset'] = offset
            safe.append(row)
        if status == 'captured' and (helper_exit != 0 or code == 0 or exception == '0x00000000'):
            raise ValueError('inconsistent capture')
        return {'status': status, 'target_exit_code': code,
                'target_exit_code_hex': f'0x{code:08X}', 'exception_code_hex': exception,
                'frames': safe}
    except (ValueError, TypeError, KeyError):
        return {'status': 'invalid_debugger_report'}


def check(root, sdk=None):
    report = {'check': 'solarcheck-opensfm-stack-1', 'status': 'not_started',
              'gpu_matching': 'not_tested', 'dataset': 'not_tested',
              'dump_created': False, 'symbols': 'local_unwind_only',
              'engine_modified': False}
    if sys.platform != 'win32' or struct.calcsize('P') != 8 or not sys.flags.isolated:
        return {**report, 'status': 'requires_isolated_windows_x64'}
    root = Path(root)
    sdk = sdk or load_buildtools()
    if (not root.is_absolute() or not root.anchor or not Path(root.anchor).exists()
            or not sdk.batch_path_supported(root)
            or any(c.isspace() or c in '()' for c in str(root))):
        return {**report, 'status': 'output_path_unsupported'}
    python = root / 'env' / 'python.exe'
    gpu = root / 'MCM_SolarCheck_OPENSFM_GPU_PRUEFUNG.py'
    if not python.is_file() or not gpu.is_file():
        return {**report, 'status': 'existing_probe_or_environment_missing'}
    if hashlib.sha256(gpu.read_bytes()).hexdigest() != GPU_HASH:
        return {**report, 'status': 'gpu_probe_hash_mismatch'}
    work = Path(tempfile.mkdtemp(prefix='stack-', dir=root))
    for name in ('temp', 'symbols', 'matplotlib'):
        (work / name).mkdir()
    compiled = compile_helper(work, sdk)
    if compiled['status'] != 'compiled':
        return {**report, **compiled}
    # Verify native capture before touching OpenSfM. These are our own two
    # disposable processes, not a repeat of the completed compiler/SDK check.
    av = run_capture(work, synthetic='av')
    clean = run_capture(work, synthetic='clean')
    if (av.get('status') != 'captured' or av.get('exception_code_hex') != '0xC0000005'
            or av.get('target_exit_code') != 0xC0000005 or len(av.get('frames', [])) < 2
            or clean.get('status') != 'clean_exit' or clean.get('target_exit_code') != 0):
        return {**report, 'status': 'capture_selftest_failed', 'synthetic_av': av, 'synthetic_clean': clean}
    captured = run_capture(work, python, gpu)
    # Capturing a crash is a diagnostic result, never a GPU/engine PASS.
    return {**report, 'status': 'diagnostic_complete', 'native_capture_selftest': 'passed',
            'inventory_process': captured, 'accepted_as_gpu_success': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', default=ROOT)
    args = parser.parse_args()
    print('Native Absturz-Aufrufkette; nur bekannter Inventarworker, keine Fotos/Dumps.', flush=True)
    try:
        report = check(args.root)
    except (OSError, ValueError, ImportError, subprocess.TimeoutExpired):
        report = {'check': 'solarcheck-opensfm-stack-1', 'status': 'diagnostic_unavailable'}
    print(json.dumps(report, indent=2, ensure_ascii=True))
    return 0 if report.get('status') == 'diagnostic_complete' else 1


if __name__ == '__main__':
    raise SystemExit(main())
