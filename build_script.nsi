; NSIS Installer Script for Xtreme ADB
; Modern UI
!include "MUI2.nsh"

; Maximum compression settings
SetCompressor /SOLID lzma
SetCompressorDictSize 64

; ==========================================
; GENERAL SETTINGS
; ==========================================
Name "Xtreme ADB"
OutFile "xadb_windows_installer_v1.3.exe"
InstallDir "$PROGRAMFILES\Xtreme ADB"
InstallDirRegKey HKLM "Software\Xtreme ADB" "Install_Dir"
RequestExecutionLevel admin

; ==========================================
; INTERFACE SETTINGS
; ==========================================
!define MUI_ABORTWARNING
!define MUI_ICON "xadb.ico"
!define MUI_UNICON "xadb.ico"

; Welcome page text
!define MUI_WELCOMEPAGE_TITLE "Welcome to Xtreme ADB Setup"
!define MUI_WELCOMEPAGE_TEXT "This installer will help you install Xtreme ADB on your device.$\r$\n$\r$\nPress Next to continue."

; ==========================================
; PAGES
; ==========================================
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "LICENSE.txt"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

; ==========================================
; LANGUAGES
; ==========================================
!insertmacro MUI_LANGUAGE "English"

; ==========================================
; INSTALLER SECTIONS
; ==========================================
Section "Xtreme ADB (Required)" SecMain
  SectionIn RO  ; Read-only, can't be unchecked
  SetOutPath "$INSTDIR"
  
  ; Copy all files from your xadb.dist folder
  File /r "xadb.dist\*.*"
  
  ; Write uninstaller
  WriteUninstaller "$INSTDIR\Uninstall.exe"
  
  ; Write registry keys for Add/Remove Programs
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Xtreme ADB" "DisplayName" "Xtreme ADB"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Xtreme ADB" "UninstallString" "$INSTDIR\Uninstall.exe"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Xtreme ADB" "DisplayIcon" "$INSTDIR\Xtreme ADB.exe"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Xtreme ADB" "Publisher" "KPR-MAN"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Xtreme ADB" "DisplayVersion" "1.3"
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Xtreme ADB" "NoModify" 1
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Xtreme ADB" "NoRepair" 1
  
  ; Save install directory
  WriteRegStr HKLM "Software\Xtreme ADB" "Install_Dir" "$INSTDIR"
SectionEnd

Section "Desktop Shortcut" SecDesktop
  CreateShortcut "$DESKTOP\Xtreme ADB.lnk" "$INSTDIR\Xtreme ADB.exe" "" "$INSTDIR\Xtreme ADB.exe" 0
SectionEnd

Section "Start Menu Shortcut" SecStartMenu
  CreateDirectory "$SMPROGRAMS\Xtreme ADB"
  CreateShortcut "$SMPROGRAMS\Xtreme ADB\Xtreme ADB.lnk" "$INSTDIR\Xtreme ADB.exe" "" "$INSTDIR\Xtreme ADB.exe" 0
  CreateShortcut "$SMPROGRAMS\Xtreme ADB\Uninstall.lnk" "$INSTDIR\Uninstall.exe"
SectionEnd

; ==========================================
; SECTION DESCRIPTIONS
; ==========================================
!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
  !insertmacro MUI_DESCRIPTION_TEXT ${SecMain} "The main Xtreme ADB application (required)"
  !insertmacro MUI_DESCRIPTION_TEXT ${SecDesktop} "Create a shortcut on the Desktop"
  !insertmacro MUI_DESCRIPTION_TEXT ${SecStartMenu} "Create shortcuts in the Start Menu"
!insertmacro MUI_FUNCTION_DESCRIPTION_END

; ==========================================
; UNINSTALLER SECTION
; ==========================================
Section "Uninstall"
  ; Remove files
  RMDir /r "$INSTDIR"
  
  ; Remove shortcuts
  Delete "$DESKTOP\Xtreme ADB.lnk"
  RMDir /r "$SMPROGRAMS\Xtreme ADB"
  
  ; Remove registry keys
  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Xtreme ADB"
  DeleteRegKey HKLM "Software\Xtreme ADB"
SectionEnd