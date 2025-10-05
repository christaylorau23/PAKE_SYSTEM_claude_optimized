@echo off
REM PAKE System Orchestrator - Test Runner (Windows)
REM Comprehensive test suite execution with coverage reporting

echo 🚀 PAKE System Orchestrator - Test Suite
echo ========================================

REM Check if we're in the right directory
if not exist "package.json" (
    echo Error: Must be run from orchestrator service directory
    exit /b 1
)

REM Install dependencies if needed
if not exist "node_modules" (
    echo 📦 Installing dependencies...
    npm install
)

echo.
echo 🔧 Building TypeScript...
npm run build
if errorlevel 1 (
    echo Build failed
    exit /b 1
)

echo.
echo 🧹 Running linter...
npm run lint
if errorlevel 1 (
    echo Linting failed
    exit /b 1
)

echo.
echo ✨ Checking code formatting...
npm run format:check
if errorlevel 1 (
    echo Formatting check failed
    exit /b 1
)

echo.
echo 📋 Validating JSON schemas...
npm run validate-schemas
if errorlevel 1 (
    echo Schema validation failed
    exit /b 1
)

echo.
echo 🧪 Running unit tests...
npm run test:unit
if errorlevel 1 (
    echo Unit tests failed
    exit /b 1
)

echo.
echo 🔗 Running integration tests...
npm run test:integration
if errorlevel 1 (
    echo Integration tests failed
    exit /b 1
)

echo.
echo 📊 Running full test suite with coverage...
npm run test:coverage
if errorlevel 1 (
    echo Coverage tests failed
    exit /b 1
)

echo.
echo 🔍 Security audit...
npm run audit-security

echo.
echo ✅ All tests passed successfully!
echo.
echo 📈 Coverage Report:
echo View detailed coverage: .\coverage\lcov-report\index.html
echo.
echo 🎯 Key Test Results:
echo • Unit Tests: Provider routing, circuit breakers, metrics
echo • Integration Tests: Full API flow, mocked providers, error handling
echo • Contract Tests: JSON schema validation, provider interfaces
echo.
echo 🎉 Phase B Implementation Complete!
