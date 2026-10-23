# Riverview Controlled Source
# File: scripts/rv_windows_resource_telemetry.ps1
# Component: WINDOWS-DEVELOPMENT-RESOURCE-TELEMETRY
# Revision: 1.0.0
# Purpose: Emit bounded read-only Windows CPU, RAM, optional NVIDIA GPU, and fixed-disk readings
# Execution Model: Invoked only as the OpenSSH forced command for the dedicated telemetry key
# Observability: rv.gpu-host-telemetry.v1 JSON with a single source timestamp
# Authority: Read-only CIM, performance counters, logical-disk queries, and nvidia-smi
# Tests: scripts/verify_v2_resource_monitor.cjs; tests/test_resource_telemetry.py
# History: Git and .riverview-backups/manifest.jsonl

Clear-Host
$ErrorActionPreference = 'Stop'
if ($env:SSH_ORIGINAL_COMMAND -ne 'rv-windows-resource-telemetry') {
  [Console]::Error.WriteLine('restricted_command_required')
  exit 77
}

$observed = [DateTime]::UtcNow.ToString('yyyy-MM-ddTHH:mm:ss.fffZ')
$cpuName = 'Unavailable'
$cpuUse = $null
$memoryTotal = $null
$memoryUsed = $null
$devices = @()
$volumes = @()

try {
  $processor = Get-CimInstance -ClassName Win32_Processor | Select-Object -First 1
  if ($processor -and $processor.Name) { $cpuName = [string]$processor.Name }
  $counter = Get-CimInstance -ClassName Win32_PerfFormattedData_PerfOS_Processor -Filter "Name='_Total'" | Select-Object -First 1
  if ($counter -and $null -ne $counter.PercentProcessorTime) { $cpuUse = [Math]::Round([double]$counter.PercentProcessorTime, 2) }
  $os = Get-CimInstance -ClassName Win32_OperatingSystem
  if ($os -and $null -ne $os.TotalVisibleMemorySize -and $null -ne $os.FreePhysicalMemory) {
    $memoryTotal = [int64]$os.TotalVisibleMemorySize * 1024
    $memoryUsed = $memoryTotal - ([int64]$os.FreePhysicalMemory * 1024)
  }
} catch {
  [Console]::Error.WriteLine('system_metrics_unavailable')
}

try {
  $nvidia = Get-Command 'nvidia-smi.exe' -ErrorAction SilentlyContinue
  if ($nvidia) {
    $rows = & $nvidia.Source '--query-gpu=name,index,utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw,fan.speed' '--format=csv,noheader,nounits' 2>$null
    foreach ($row in $rows) {
      $parts = [string]$row -split ',\s*'
      if ($parts.Count -ne 8) { continue }
      $index = 0; $util = $null; $usedMb = $null; $totalMb = $null; $temp = $null; $power = $null; $fan = $null
      if (-not [int]::TryParse($parts[1], [ref]$index)) { continue }
      $number = 0
      if ([int]::TryParse($parts[2], [ref]$number) -and $number -le 100) { $util = $number }
      if ([int]::TryParse($parts[3], [ref]$number)) { $usedMb = $number }
      if ([int]::TryParse($parts[4], [ref]$number)) { $totalMb = $number }
      if ([int]::TryParse($parts[5], [ref]$number) -and $number -le 200) { $temp = $number }
      $decimal = 0.0
      if ([double]::TryParse($parts[6], [Globalization.NumberStyles]::Float, [Globalization.CultureInfo]::InvariantCulture, [ref]$decimal) -and $decimal -ge 0 -and $decimal -le 10000) { $power = $decimal }
      if ([int]::TryParse($parts[7], [ref]$number) -and $number -le 100) { $fan = $number }
      $usedBytes = $null
      $totalBytes = $null
      if ($null -ne $usedMb) { $usedBytes = [int64]$usedMb * 1MB }
      if ($null -ne $totalMb) { $totalBytes = [int64]$totalMb * 1MB }
      $devices += [ordered]@{index=$index;name=$parts[0];utilization_percent=$util;memory_used_bytes=$usedBytes;memory_total_bytes=$totalBytes;temperature_celsius=$temp;power_watts=$power;fan_percent=$fan;active_services=@()}
    }
  }
} catch {
  $devices = @()
}

try {
  $driveIndex = 0
  foreach ($disk in (Get-CimInstance -ClassName Win32_LogicalDisk -Filter 'DriveType=3' | Sort-Object DeviceID)) {
    if ($disk.Size -gt 0 -and $disk.FreeSpace -ge 0 -and $disk.FreeSpace -le $disk.Size -and $disk.FileSystem -in @('NTFS','ReFS','FAT32','exFAT')) {
      $used = [int64]$disk.Size - [int64]$disk.FreeSpace
      $volumes += [ordered]@{major_minor="0:$driveIndex";filesystem_type=$disk.FileSystem.ToLowerInvariant();source=[string]$disk.DeviceID;mount_point=[string]$disk.DeviceID;total_bytes=[int64]$disk.Size;used_bytes=$used;available_bytes=[int64]$disk.FreeSpace;observed_at=$observed}
      $driveIndex++
    }
  }
} catch {
  $volumes = @()
}

$report = [ordered]@{
  schema_version = 'rv.gpu-host-telemetry.v1'
  observed_at = $observed
  host_metrics = [ordered]@{observed_at=$observed;cpu_name=$cpuName;cpu_utilization_percent=$cpuUse;memory_total_bytes=$memoryTotal;memory_used_bytes=$memoryUsed}
  devices = @($devices)
  storage_volumes = @($volumes)
}
ConvertTo-Json -InputObject $report -Depth 6 -Compress
