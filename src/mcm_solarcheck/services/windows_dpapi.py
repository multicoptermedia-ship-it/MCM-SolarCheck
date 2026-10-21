"""Windows DPAPI (current-user scope) via standard-library ctypes.

Uses CryptProtectData / CryptUnprotectData without LOCAL_MACHINE or UI prompts.
No secrets or Win32 error messages are displayed in desktop status strings.
The OS-bound guarantee requires real Windows testing; Linux CI mocks this boundary.
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes
import sys


class _DataBlob(ctypes.Structure):
    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_ubyte)),
    ]


def _dpapi(data: bytes, *, decrypt: bool) -> bytes:
    if sys.platform != "win32":
        raise OSError("Windows DPAPI unavailable")
    if not isinstance(data, bytes) or not (0 < len(data) <= 4096):
        raise ValueError("invalid DPAPI payload length")
    crypt32 = ctypes.WinDLL("Crypt32.dll", use_last_error=True)
    kernel = ctypes.WinDLL("Kernel32.dll", use_last_error=True)
    buffer = (ctypes.c_ubyte * len(data)).from_buffer_copy(data)
    input_blob = _DataBlob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)))
    output_blob = _DataBlob()
    ptr = ctypes.POINTER(_DataBlob)
    call = crypt32.CryptUnprotectData if decrypt else crypt32.CryptProtectData
    call.argtypes = [
        ptr, ctypes.c_void_p if decrypt else wintypes.LPCWSTR,
        ptr, ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ptr,
    ]
    call.restype = wintypes.BOOL
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p
    try:
        ok = call(
            ctypes.byref(input_blob), None, None, None, None,
            1,  # CRYPTPROTECT_UI_FORBIDDEN; never LOCAL_MACHINE
            ctypes.byref(output_blob),
        )
        if not ok:
            raise OSError("Windows DPAPI protection operation failed")
        if not 0 < output_blob.cbData <= 4096 or not output_blob.pbData:
            raise OSError("Windows DPAPI returned invalid data")
        return ctypes.string_at(output_blob.pbData, output_blob.cbData)
    finally:
        if output_blob.pbData:
            kernel.LocalFree(ctypes.cast(output_blob.pbData, ctypes.c_void_p))


def protect_for_current_user(plaintext: bytes) -> bytes:
    return _dpapi(plaintext, decrypt=False)


def unprotect_for_current_user(ciphertext: bytes) -> bytes:
    return _dpapi(ciphertext, decrypt=True)
