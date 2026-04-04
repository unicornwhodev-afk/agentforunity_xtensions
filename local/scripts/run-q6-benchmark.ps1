<#
    AgentUnity - Run the local Q6 benchmark flow from Windows.
    Supports environment setup, case generation, benchmark execution, and visualization.
#>

[CmdletBinding()]
param(
    [ValidateSet("setup", "prepare", "run", "visualize", "all")]
    [string]$Mode = "all",

    [string]$TrainingRepoPath,
    [string]$PythonPath,
    [string]$VenvPath,
    [string]$LlamaDir,
    [string]$RegistryPath,
    [string]$CasesPath,
    [string]$ResultsPath,
    [string]$OutputPrefix,
    [string]$CacheDir,
    [string]$LlamaCppCmakeFlag = "-DGGML_CUDA=ON",

    [int]$CaseLimit = 0,
    [int]$MaxNewTokens = 448,
    [int]$GpuLayers = -1,
    [int]$ContextSize = 8192,
    [int]$Threads = 0,

    [double[]]$TensorSplit,
    [string[]]$ModelIds
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$LocalDir = Split-Path -Parent $ScriptDir
$RepoRoot = Split-Path -Parent $LocalDir

if (-not $TrainingRepoPath -and $env:AGENTUNITY_TRAINING_REPO) {
    $TrainingRepoPath = $env:AGENTUNITY_TRAINING_REPO
}

$TrainRoot = if ($TrainingRepoPath -and (Test-Path $TrainingRepoPath)) { (Resolve-Path $TrainingRepoPath).Path } else { $TrainingRepoPath }
$BenchmarkDir = Join-Path $TrainRoot "benchmark"
$ResultsDir = Join-Path $TrainRoot "benchmark-results"
$DefaultCacheDir = Join-Path $TrainRoot ".cache\agentunity-q6-benchmark"
$DefaultVenvPath = Join-Path $RepoRoot ".venv-q6-benchmark"
$DefaultLlamaDir = Join-Path $env:USERPROFILE "tools\llama.cpp"
$IsWindowsHost = $PSVersionTable.Platform -eq "Win32NT" -or $env:OS -eq "Windows_NT"

if (-not $VenvPath) {
    $VenvPath = $DefaultVenvPath
}
if (-not $LlamaDir) {
    $LlamaDir = $DefaultLlamaDir
}
if (-not $RegistryPath) {
    $RegistryPath = Join-Path $BenchmarkDir "benchmark_q6_gguf_registry.example.json"
}
if (-not $CasesPath) {
    $CasesPath = Join-Path $BenchmarkDir "benchmark_cases_advanced_150.json"
}
if (-not $ResultsPath) {
    $ResultsPath = Join-Path $ResultsDir "q6-advanced-150-results.json"
}
if (-not $OutputPrefix) {
    $OutputPrefix = Join-Path $ResultsDir "q6-advanced-150"
}
if (-not $CacheDir) {
    $CacheDir = $DefaultCacheDir
}

$VenvPython = Join-Path $VenvPath "Scripts\python.exe"

function Write-Section {
    param([string]$Title)

    Write-Host ""
    Write-Host "== $Title ==" -ForegroundColor Cyan
}

function Invoke-External {
    param(
        [Parameter(Mandatory = $true)]
        [string]$FilePath,

        [string[]]$Arguments = @(),

        [string]$WorkingDirectory = $RepoRoot,

        [hashtable]$ExtraEnvironment = @{}
    )

    $resolvedFilePath = $FilePath
    if (-not (Split-Path $FilePath -IsAbsolute)) {
        $command = Get-Command $FilePath -ErrorAction Stop
        $resolvedFilePath = $command.Source
    }

    Write-Host ("-> " + $resolvedFilePath + " " + ($Arguments -join " ")) -ForegroundColor DarkGray

    $previousLocation = Get-Location
    $envBackup = @{}

    try {
        Set-Location $WorkingDirectory
        foreach ($entry in $ExtraEnvironment.GetEnumerator()) {
            $envBackup[$entry.Key] = [Environment]::GetEnvironmentVariable($entry.Key, "Process")
            [Environment]::SetEnvironmentVariable($entry.Key, [string]$entry.Value, "Process")
        }

        & $resolvedFilePath @Arguments
        if ($LASTEXITCODE -ne 0) {
            throw "Command failed with exit code $LASTEXITCODE"
        }
    }
    finally {
        foreach ($entry in $ExtraEnvironment.GetEnumerator()) {
            [Environment]::SetEnvironmentVariable($entry.Key, $envBackup[$entry.Key], "Process")
        }
        Set-Location $previousLocation
    }
}

function Resolve-ExistingPath {
    param([string]$PathValue)

    if ($PathValue -and (Test-Path $PathValue)) {
        return (Resolve-Path $PathValue).Path
    }

    return $PathValue
}

function Assert-TrainingRepoAvailable {
    if (-not $TrainRoot) {
        throw "Training repo path is not configured. Provide -TrainingRepoPath or set AGENTUNITY_TRAINING_REPO."
    }

    if (-not (Test-Path $TrainRoot)) {
        throw "Training repo not found: $TrainRoot. Provide -TrainingRepoPath or set AGENTUNITY_TRAINING_REPO."
    }

    if (-not (Test-Path $BenchmarkDir)) {
        throw "Benchmark directory not found in training repo: $BenchmarkDir"
    }
}

function Get-BootstrapPython {
    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) {
        return @{ FilePath = $py.Source; PrefixArgs = @("-3") }
    }

    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) {
        return @{ FilePath = $python.Source; PrefixArgs = @() }
    }

    throw "No Python launcher found. Install Python or provide -PythonPath."
}

function Get-RunPython {
    if ($PythonPath) {
        return Resolve-ExistingPath -PathValue $PythonPath
    }

    if (Test-Path $VenvPython) {
        return (Resolve-Path $VenvPython).Path
    }

    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) {
        return $python.Source
    }

    throw "No Python interpreter available. Run with -Mode setup first or provide -PythonPath."
}

function Get-NinjaExecutable {
    $venvNinja = Join-Path $VenvPath "Scripts\ninja.exe"
    if (Test-Path $venvNinja) {
        return (Resolve-Path $venvNinja).Path
    }

    $ninja = Get-Command ninja -ErrorAction SilentlyContinue
    if ($ninja) {
        return $ninja.Source
    }

    throw "Ninja was not found. Install it in the venv or on PATH."
}

function Get-VcVarsPath {
    $candidates = @(
        "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat",
        "C:\Program Files\Microsoft Visual Studio\2022\Professional\VC\Auxiliary\Build\vcvars64.bat",
        "C:\Program Files\Microsoft Visual Studio\2022\Enterprise\VC\Auxiliary\Build\vcvars64.bat",
        "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
    )

    foreach ($candidate in $candidates) {
        if (Test-Path $candidate) {
            return $candidate
        }
    }

    $vswhere = Join-Path ${env:ProgramFiles(x86)} "Microsoft Visual Studio\Installer\vswhere.exe"
    if (Test-Path $vswhere) {
        $installPath = & $vswhere -latest -products * -property installationPath 2>$null
        if ($LASTEXITCODE -eq 0 -and $installPath) {
            $candidate = Join-Path $installPath "VC\Auxiliary\Build\vcvars64.bat"
            if (Test-Path $candidate) {
                return $candidate
            }
        }
    }

    throw "Visual Studio developer tools were not found. Install Visual Studio C++ tools."
}

function Invoke-CmdBatch {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Lines,

        [string]$WorkingDirectory = $RepoRoot
    )

    $scriptPath = Join-Path $env:TEMP ("agentunity-" + [guid]::NewGuid().ToString("N") + ".cmd")
    $content = @("@echo off") + $Lines

    try {
        $content | Set-Content -Path $scriptPath -Encoding ASCII
        Invoke-External -FilePath "cmd.exe" -Arguments @("/c", $scriptPath) -WorkingDirectory $WorkingDirectory
    }
    finally {
        Remove-Item $scriptPath -Force -ErrorAction SilentlyContinue
    }
}

function Invoke-WindowsCudaBuildCommand {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Commands,

        [string]$WorkingDirectory = $RepoRoot
    )

    $vcvarsPath = Get-VcVarsPath
    $lines = @(
        "call `"$vcvarsPath`""
    ) + $Commands

    Invoke-CmdBatch -Lines $lines -WorkingDirectory $WorkingDirectory
}

function Ensure-Directory {
    param([string]$Path)

    if (-not (Test-Path $Path)) {
        New-Item -ItemType Directory -Path $Path -Force | Out-Null
    }
}

function Clear-OutputArtifacts {
    param(
        [switch]$IncludeResults
    )

    $outputDirectory = Split-Path -Parent $OutputPrefix
    $outputName = Split-Path -Leaf $OutputPrefix
    Ensure-Directory $outputDirectory

    Get-ChildItem -Path $outputDirectory -Filter "$outputName*" -ErrorAction SilentlyContinue |
        Where-Object {
            if ($IncludeResults) {
                return $true
            }

            return $_.FullName -ne $ResultsPath
        } |
        Remove-Item -Force -Recurse
}

function Setup-BenchmarkEnvironment {
    Write-Section "Benchmark Environment Setup"

    Assert-TrainingRepoAvailable

    Ensure-Directory $CacheDir

    if (-not (Test-Path $VenvPython)) {
        $bootstrap = Get-BootstrapPython
        Write-Host "Creating virtual environment: $VenvPath" -ForegroundColor Yellow
        Invoke-External -FilePath $bootstrap.FilePath -Arguments ($bootstrap.PrefixArgs + @("-m", "venv", $VenvPath))
    }
    else {
        Write-Host "Virtual environment already exists: $VenvPath" -ForegroundColor Green
    }

    $resolvedVenvPython = Resolve-ExistingPath -PathValue $VenvPython
    $resolvedLlamaDir = Resolve-ExistingPath -PathValue $LlamaDir

    Invoke-External -FilePath $resolvedVenvPython -Arguments @("-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel")
    Invoke-External -FilePath $resolvedVenvPython -Arguments @("-m", "pip", "install", "cmake", "ninja", "gguf", "huggingface_hub", "numpy", "safetensors", "sentencepiece", "transformers")

    if (-not (Test-Path $resolvedLlamaDir)) {
        Write-Host "Cloning llama.cpp into $resolvedLlamaDir" -ForegroundColor Yellow
        Invoke-External -FilePath "git" -Arguments @("clone", "--depth=1", "https://github.com/ggerganov/llama.cpp.git", $resolvedLlamaDir)
    }
    else {
        Write-Host "Updating llama.cpp in $resolvedLlamaDir" -ForegroundColor Yellow
        Invoke-External -FilePath "git" -Arguments @("-C", $resolvedLlamaDir, "pull", "--ff-only")
    }

    $cmakeExe = Resolve-ExistingPath -PathValue (Join-Path $VenvPath "Scripts\cmake.exe")
    $ninjaExe = Get-NinjaExecutable
    $buildDir = Join-Path $resolvedLlamaDir "build"

    if ($IsWindowsHost -and $LlamaCppCmakeFlag -match "GGML_CUDA=ON") {
        Write-Host "Using Visual Studio developer environment + Ninja for Windows CUDA build" -ForegroundColor Yellow
        Invoke-WindowsCudaBuildCommand -Commands @(
            "if exist `"$buildDir\CMakeCache.txt`" del /f /q `"$buildDir\CMakeCache.txt`"",
            "if exist `"$buildDir\CMakeFiles`" rmdir /s /q `"$buildDir\CMakeFiles`"",
            "`"$cmakeExe`" -S `"$resolvedLlamaDir`" -B `"$buildDir`" -G Ninja -DCMAKE_MAKE_PROGRAM=`"$ninjaExe`" $LlamaCppCmakeFlag -DCMAKE_BUILD_TYPE=Release",
            "`"$cmakeExe`" --build `"$buildDir`" --config Release -j",
            "set CMAKE_GENERATOR=Ninja",
            "set CMAKE_ARGS=$LlamaCppCmakeFlag -DCMAKE_MAKE_PROGRAM=`"$ninjaExe`"",
            "set FORCE_CMAKE=1",
            "`"$resolvedVenvPython`" -m pip install --upgrade --force-reinstall --no-cache-dir llama-cpp-python"
        )
    }
    else {
        Invoke-External -FilePath $cmakeExe -Arguments @("-S", $resolvedLlamaDir, "-B", $buildDir, $LlamaCppCmakeFlag, "-DCMAKE_BUILD_TYPE=Release")
        Invoke-External -FilePath $cmakeExe -Arguments @("--build", $buildDir, "--config", "Release", "-j")

        Invoke-External -FilePath $resolvedVenvPython -Arguments @("-m", "pip", "install", "--upgrade", "--force-reinstall", "--no-cache-dir", "llama-cpp-python") -ExtraEnvironment @{
            "CMAKE_ARGS" = $LlamaCppCmakeFlag
            "FORCE_CMAKE" = "1"
        }
    }

    Write-Host "Setup complete." -ForegroundColor Green
    Write-Host "Python: $resolvedVenvPython" -ForegroundColor Gray
    Write-Host "llama.cpp: $resolvedLlamaDir" -ForegroundColor Gray
}

function Prepare-Cases {
    Write-Section "Generate Benchmark Cases"
    Assert-TrainingRepoAvailable
    $pythonExe = Get-RunPython
    Invoke-External -FilePath $pythonExe -Arguments @((Join-Path $BenchmarkDir "build_advanced_benchmark_cases.py"), "--output-path", $CasesPath)
}

function Run-Benchmark {
    Write-Section "Run Benchmark"
    Assert-TrainingRepoAvailable
    $pythonExe = Get-RunPython

    Ensure-Directory $ResultsDir
    Ensure-Directory $CacheDir
    Clear-OutputArtifacts -IncludeResults

    $arguments = @(
        (Join-Path $BenchmarkDir "benchmark_q6_gguf.py"),
        "--registry-path", $RegistryPath,
        "--cases-path", $CasesPath,
        "--output-path", $ResultsPath,
        "--cache-dir", $CacheDir,
        "--max-new-tokens", $MaxNewTokens,
        "--case-limit", $CaseLimit,
        "--n-gpu-layers", $GpuLayers,
        "--n-ctx", $ContextSize
    )

    if ($Threads -gt 0) {
        $arguments += @("--threads", $Threads)
    }
    if ($ModelIds.Count -gt 0) {
        $arguments += "--model-ids"
        foreach ($modelId in $ModelIds) {
            $arguments += $modelId
        }
    }
    if ($TensorSplit) {
        $arguments += "--tensor-split"
        foreach ($value in $TensorSplit) {
            $arguments += [string]$value
        }
    }

    Invoke-External -FilePath $pythonExe -Arguments $arguments -ExtraEnvironment @{
        "HF_HOME" = (Join-Path $TrainRoot ".cache\huggingface")
        "TRANSFORMERS_CACHE" = (Join-Path $TrainRoot ".cache\huggingface\hub")
    }
}

function Visualize-Benchmark {
    Write-Section "Visualize Benchmark Results"
    Assert-TrainingRepoAvailable
    $pythonExe = Get-RunPython

    if (-not (Test-Path $ResultsPath)) {
        throw "Benchmark results not found: $ResultsPath"
    }

    Clear-OutputArtifacts
    Invoke-External -FilePath $pythonExe -Arguments @(
        (Join-Path $BenchmarkDir "benchmark_visualize_results.py"),
        "--input-path", $ResultsPath,
        "--cases-path", $CasesPath,
        "--output-prefix", $OutputPrefix
    )
}

Write-Host ""
Write-Host "AgentUnity - Local Q6 Benchmark Driver" -ForegroundColor Cyan
Write-Host "Repo root: $RepoRoot" -ForegroundColor DarkGray
Write-Host "Training repo: $TrainRoot" -ForegroundColor DarkGray
Write-Host "Mode: $Mode" -ForegroundColor DarkGray

switch ($Mode) {
    "setup" {
        Setup-BenchmarkEnvironment
    }
    "prepare" {
        Prepare-Cases
    }
    "run" {
        Prepare-Cases
        Run-Benchmark
    }
    "visualize" {
        Visualize-Benchmark
    }
    "all" {
        Prepare-Cases
        Run-Benchmark
        Visualize-Benchmark
    }
}

Write-Host "" 
Write-Host "Completed." -ForegroundColor Green