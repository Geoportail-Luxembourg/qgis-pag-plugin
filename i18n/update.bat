@echo off
setlocal enabledelayedexpansion
set files=
for /f %%f in ('dir /b /s "c:\Users\arxit\.qgis2\python\plugins\PagLuxembourg\*.py" "c:\Users\arxit\.qgis2\python\plugins\PagLuxembourg\*.ui"') do set files=!files! %%f
"C:\Program Files\QGIS Wien\bin\pylupdate4"%files% -ts C:\Users\arxit\.qgis2\python\plugins\PagLuxembourg\i18n\fr.ts