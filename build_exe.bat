@echo off
rem Dong goi "Ghep anh thong minh" thanh file .exe (chi can chay 1 lan moi phien ban)
cd /d "%~dp0"

echo === Buoc 1/3: cai PyInstaller (neu chua co) ===
python -m pip install --upgrade pyinstaller || goto :err

echo.
echo === Buoc 2/3: dong goi (mat 1-3 phut) ===
python -m PyInstaller GhepAnh.spec --noconfirm --clean || goto :err

echo.
echo === Buoc 3/3: ky so (Datpro09) + dua exe ra thu muc goc ===
powershell -NoProfile -ExecutionPolicy Bypass -File "packaging\sign_exe.ps1" || goto :err
copy /Y "dist\GhepAnh.exe" "GhepAnh.exe" >nul
copy /Y "dist\ghep.exe" "ghep.exe" >nul

echo.
echo ================= XONG! =================
echo   GhepAnh.exe  - giao dien, ngay thu muc goc (nhay dup de chay)
echo   ghep.exe     - dong lenh:  ghep.exe "D:\Anh" -l timeline
echo   Da ky so (chung chi tu ky Datpro09 - xem packaging\Datpro09.cer)
echo ==========================================
pause
exit /b 0

:err
echo.
echo Loi khi dong goi - xem thong bao phia tren.
pause
exit /b 1
