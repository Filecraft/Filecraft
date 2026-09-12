/* Apache-2.0. GUI-only bootstrap; console runtime remains byte-for-byte intact.
 * CLI/worker callers must invoke Filecraft-Desktop.exe directly, not this stub.
 * CREATE_NO_WINDOW avoids a console flash without changing worker pipe handling.
 */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <wchar.h>

int WINAPI wWinMain(HINSTANCE instance, HINSTANCE previous, PWSTR arguments, int show) {
    wchar_t path[32768];
    wchar_t command[32768];
    wchar_t *slash;
    STARTUPINFOW startup = {0};
    PROCESS_INFORMATION process = {0};
    DWORD length;
    DWORD status = 1;
    (void)instance; (void)previous; (void)show;
    if (arguments && *arguments) {
        MessageBoxW(NULL, L"Use Filecraft-Desktop.exe for command-line or worker operations.", L"Filecraft", MB_OK | MB_ICONERROR);
        return 2;
    }
    length = GetModuleFileNameW(NULL, path, 32768);
    if (!length || length >= 32768) return 1;
    slash = wcsrchr(path, L'\\');
    if (!slash) return 1;
    *slash = L'\0';
    if (swprintf_s(command, 32768, L"\"%ls\\Filecraft-Desktop.exe\"", path) < 0) return 1;
    /* Explicit executable path prevents ambiguous CreateProcess path parsing. */
    {
        wchar_t executable[32768];
        if (swprintf_s(executable, 32768, L"%ls\\Filecraft-Desktop.exe", path) < 0) return 1;
        startup.cb = sizeof(startup);
        if (!CreateProcessW(executable, command, NULL, NULL, FALSE, CREATE_NO_WINDOW,
                            NULL, path, &startup, &process)) {
            MessageBoxW(NULL, L"Filecraft could not start. Reinstall the complete package.", L"Filecraft", MB_OK | MB_ICONERROR);
            return 1;
        }
    }
    CloseHandle(process.hThread);
    WaitForSingleObject(process.hProcess, INFINITE);
    GetExitCodeProcess(process.hProcess, &status);
    CloseHandle(process.hProcess);
    return (int)status;
}
