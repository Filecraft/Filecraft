/* CI-only runner: remove privilege; never elevate or relax system policy. */
#define UNICODE
#define _UNICODE
#include <windows.h>
#include <sddl.h>
#include <stdio.h>
#include <wchar.h>
static int fail(const wchar_t *where){fwprintf(stderr,L"%ls failed: %lu\n",where,GetLastError());return 1;}
int wmain(int argc,wchar_t **argv){
 if(argc!=3){fwprintf(stderr,L"usage: restricted-run pwsh.exe script.ps1\n");return 2;}
 HANDLE original=NULL,restricted=NULL;PSID admin=NULL,power=NULL,medium=NULL;
 if(!OpenProcessToken(GetCurrentProcess(),TOKEN_DUPLICATE|TOKEN_QUERY|TOKEN_ASSIGN_PRIMARY|TOKEN_ADJUST_DEFAULT,&original))return fail(L"OpenProcessToken");
 if(!ConvertStringSidToSidW(L"S-1-5-32-544",&admin)||!ConvertStringSidToSidW(L"S-1-5-32-547",&power))return fail(L"Group SID");
 SID_AND_ATTRIBUTES deny[2]={{admin,0},{power,0}};
 if(!CreateRestrictedToken(original,DISABLE_MAX_PRIVILEGE|LUA_TOKEN,2,deny,0,NULL,0,NULL,&restricted))return fail(L"CreateRestrictedToken");
 if(!ConvertStringSidToSidW(L"S-1-16-8192",&medium))return fail(L"Medium SID");
 TOKEN_MANDATORY_LABEL label;label.Label.Sid=medium;label.Label.Attributes=SE_GROUP_INTEGRITY;
 if(!SetTokenInformation(restricted,TokenIntegrityLevel,&label,sizeof(label)+GetLengthSid(medium)))return fail(L"Set medium integrity");
 wchar_t command[32768];if(swprintf_s(command,32768,L"\"%ls\" -NoProfile -ExecutionPolicy RemoteSigned -File \"%ls\"",argv[1],argv[2])<0)return 2;
 /* Explicitly grant the restricted user's SID its own process/thread objects.
    Elevated defaults can make the medium child unable to create descendants. */
 DWORD length=0;GetTokenInformation(restricted,TokenUser,NULL,0,&length);
 TOKEN_USER *user=(TOKEN_USER*)LocalAlloc(LPTR,length);wchar_t *sid=NULL;
 if(!user||!GetTokenInformation(restricted,TokenUser,user,length,&length)||!ConvertSidToStringSidW(user->User.Sid,&sid))return fail(L"Token user");
 wchar_t sddl[512];swprintf_s(sddl,512,L"D:(A;;GA;;;%ls)S:(ML;;NW;;;ME)",sid);
 PSECURITY_DESCRIPTOR descriptor=NULL;
 if(!ConvertStringSecurityDescriptorToSecurityDescriptorW(sddl,SDDL_REVISION_1,&descriptor,NULL))return fail(L"Child security descriptor");
 SECURITY_ATTRIBUTES security={sizeof(security),descriptor,FALSE};
 STARTUPINFOW si={sizeof(si)};PROCESS_INFORMATION pi={0};si.lpDesktop=L"winsta0\\default";
 if(!CreateProcessAsUserW(restricted,argv[1],command,&security,&security,FALSE,0,NULL,NULL,&si,&pi))return fail(L"CreateProcessAsUser");
 DWORD wait=WaitForSingleObject(pi.hProcess,600000),code=1;
 if(wait==WAIT_OBJECT_0)GetExitCodeProcess(pi.hProcess,&code);else {TerminateProcess(pi.hProcess,1);fwprintf(stderr,L"Restricted test timeout\n");}
 LocalFree(descriptor);LocalFree(sid);LocalFree(user);
 CloseHandle(pi.hThread);CloseHandle(pi.hProcess);CloseHandle(restricted);CloseHandle(original);LocalFree(admin);LocalFree(power);LocalFree(medium);return (int)code;
}
