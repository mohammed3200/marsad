; NSIS installer for مرصد (marsad)
; Build from the repo root after `pyinstaller marsad.spec`:
;   makensis -DVERSION=1.0.0 packaging\windows\marsad.nsi
; Produces dist\marsad-setup-<version>.exe

Unicode true

!define APPNAME   "marsad"
!ifndef VERSION
  !define VERSION "0.0.0"
!endif
!define PUBLISHER "LTT PMO"
!define UNINSTKEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}"

Name "مرصد (marsad)"
OutFile "dist\marsad-setup-${VERSION}.exe"
InstallDir "$PROGRAMFILES64\${APPNAME}"
InstallDirRegKey HKLM "Software\${APPNAME}" "InstallDir"
RequestExecutionLevel admin

!include "MUI2.nsh"
!define MUI_ICON   "assets\marsad.ico"
!define MUI_UNICON "assets\marsad.ico"

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!define MUI_FINISHPAGE_RUN "$INSTDIR\marsad.exe"
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "English"

Section "Install"
  SetOutPath "$INSTDIR"
  File /r "dist\marsad\*.*"

  CreateDirectory "$SMPROGRAMS\${APPNAME}"
  CreateShortcut  "$SMPROGRAMS\${APPNAME}\${APPNAME}.lnk" "$INSTDIR\marsad.exe" "" "$INSTDIR\marsad.exe"
  CreateShortcut  "$DESKTOP\${APPNAME}.lnk"               "$INSTDIR\marsad.exe" "" "$INSTDIR\marsad.exe"

  WriteRegStr HKLM "Software\${APPNAME}" "InstallDir" "$INSTDIR"
  WriteRegStr HKLM "${UNINSTKEY}" "DisplayName"     "مرصد (marsad)"
  WriteRegStr HKLM "${UNINSTKEY}" "DisplayVersion"  "${VERSION}"
  WriteRegStr HKLM "${UNINSTKEY}" "Publisher"       "${PUBLISHER}"
  WriteRegStr HKLM "${UNINSTKEY}" "DisplayIcon"     "$INSTDIR\marsad.exe"
  WriteRegStr HKLM "${UNINSTKEY}" "UninstallString" "$INSTDIR\uninstall.exe"
  WriteRegDWORD HKLM "${UNINSTKEY}" "NoModify" 1
  WriteRegDWORD HKLM "${UNINSTKEY}" "NoRepair" 1

  WriteUninstaller "$INSTDIR\uninstall.exe"
SectionEnd

Section "Uninstall"
  Delete "$SMPROGRAMS\${APPNAME}\${APPNAME}.lnk"
  RMDir  "$SMPROGRAMS\${APPNAME}"
  Delete "$DESKTOP\${APPNAME}.lnk"
  RMDir /r "$INSTDIR"
  DeleteRegKey HKLM "${UNINSTKEY}"
  DeleteRegKey HKLM "Software\${APPNAME}"
SectionEnd
