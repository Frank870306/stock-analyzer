@echo off
cd /d "C:\Users\user\OneDrive\桌面\程式"
git add .
git commit -m "自動同步 %date% %time%"
git push origin master
pause
