// Z7Trace.h — lightweight tracing for 7-Zip source instrumentation
//
// Build with -DZ7_TRACE_ENABLE to activate.  When not defined, all macros
// compile away to nothing — zero overhead in production/release builds.
//
// Output goes to both:
//   1. OutputDebugStringA  — visible in Sysinternals DebugView / DbgView++
//   2. (optional) a log file — define Z7_TRACE_LOGFILE before including this
//      header, e.g.:
//        #define Z7_TRACE_LOGFILE "C:\\Temp\\7z_trace.log"
//
// Usage:
//   Z7TRACE("message");
//   Z7TRACE("WF: %s  index=%u  path=%ls", label, idx, wpath);
//   Z7TRACE_W(wideStr);        // log a single wide string
//   Z7TRACE_ENTER(funcname);   // logs ">>> funcname"
//   Z7TRACE_LEAVE(funcname);   // logs "<<< funcname"

#pragma once

#ifdef Z7_TRACE_ENABLE

#ifndef _WIN32_WINNT
#define _WIN32_WINNT 0x0500
#endif
#include <windows.h>
#include <stdio.h>
#include <share.h>

// ---- internal helpers -------------------------------------------------------

// Default log file path — matches docs/7zip/automation-tests/app-config.json.
// Override by defining Z7_TRACE_LOGFILE before including this header, or on
// the compiler command line with /DZ7_TRACE_LOGFILE=...
#ifndef Z7_TRACE_LOGFILE
#define Z7_TRACE_LOGFILE "C:\\Temp\\7z_trace.log"
#endif

#ifdef Z7_TRACE_LOGFILE
namespace _Z7TraceImpl {
  inline FILE* _GetLog() {
    static FILE* _f = NULL;
    // _SH_DENYNO = full sharing (read + write). Allows the test harness
    // to read the log while 7zFM still has it open for appending.
    if (!_f) { _f = _fsopen(Z7_TRACE_LOGFILE, "a", _SH_DENYNO); }
    return _f;
  }
}
#define _Z7TRACE_FILE_WRITE(buf) do { \
    FILE* _f = _Z7TraceImpl::_GetLog(); \
    if (_f) { fputs((buf), _f); fflush(_f); } \
} while(0)
#else
#define _Z7TRACE_FILE_WRITE(buf) ((void)0)
#endif

namespace _Z7TraceImpl {
  inline void Write(const char* buf) {
    OutputDebugStringA(buf);
    _Z7TRACE_FILE_WRITE(buf);
  }
  inline void Fmt(const char* fmt, ...) {
    char buf[1024];
    va_list va;
    va_start(va, fmt);
    vsnprintf(buf, sizeof(buf) - 1, fmt, va);
    buf[sizeof(buf) - 1] = '\0';
    va_end(va);
    Write(buf);
  }
}

// ---- public macros ----------------------------------------------------------

// General formatted trace (printf-style)
#define Z7TRACE(fmt, ...) \
    _Z7TraceImpl::Fmt("[7z] " fmt "\n", ##__VA_ARGS__)

// Trace a single wide-char string (converts via WideCharToMultiByte)
#define Z7TRACE_W(wstr) do { \
    char _tb[512]; \
    WideCharToMultiByte(CP_UTF8, 0, (wstr), -1, _tb, sizeof(_tb), NULL, NULL); \
    _tb[sizeof(_tb)-1] = '\0'; \
    Z7TRACE("[W] %s", _tb); \
} while(0)

// Function entry / leave
#define Z7TRACE_ENTER(fn) Z7TRACE(">>> " fn)
#define Z7TRACE_LEAVE(fn) Z7TRACE("<<< " fn)

#else // Z7_TRACE_ENABLE not defined — everything compiles away

#define Z7TRACE(...)         ((void)0)
#define Z7TRACE_W(wstr)      ((void)0)
#define Z7TRACE_ENTER(fn)    ((void)0)
#define Z7TRACE_LEAVE(fn)    ((void)0)

#endif // Z7_TRACE_ENABLE
