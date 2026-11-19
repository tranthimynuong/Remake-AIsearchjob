@echo off
chcp 65001 > nul
echo ======================================================================
echo           DANG TU DONG TIM VIEC LAM PHU HOP TAI TP.HCM...
echo ======================================================================
python tools/job_finder.py
echo.
echo ======================================================================
echo DA HOAN TAT! Ban co the mo file job_search_results.md hoac .csv de xem.
echo ======================================================================
pause
