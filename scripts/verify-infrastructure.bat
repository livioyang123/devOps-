@echo off
REM Infrastructure Verification Script for Windows
REM This script verifies that all Docker services are running correctly

echo ========================================
echo DevOps K8s Platform - Infrastructure Verification
echo ========================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ and try again
    exit /b 1
)

REM Run the Python verification script
python scripts\verify-infrastructure.py

exit /b %ERRORLEVEL%
