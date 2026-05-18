param(
    [string]$Output = "media/demo_record.mp4",
    [int]$Duration = 8,
    [int]$Fps = 30,
    [string]$Device = ""
)

if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    Write-Host "ffmpeg not found on PATH. Please install ffmpeg first." -ForegroundColor Red
    exit 1
}

if ([string]::IsNullOrWhiteSpace($Device)) {
    Write-Host "No device specified. To list devices run:`n  ffmpeg -list_devices true -f dshow -i dummy`" -ForegroundColor Yellow
    exit 1
}

$escapedDevice = $Device.Replace('"','\"')
$recordCmd = "ffmpeg -f dshow -i video=\"$escapedDevice\" -t $Duration -r $Fps -y $Output"
Write-Host "Recording to $Output for $Duration seconds from device: $Device"
Write-Host "Running: $recordCmd"

iex $recordCmd

# Create a GIF version
$gif = [System.IO.Path]::ChangeExtension($Output, ".gif")
$gifCmd = "ffmpeg -i $Output -vf ""fps=$([string]$Fps/2),scale=640:-1:flags=lanczos"" -y $gif"
Write-Host "Converting to GIF: $gif"
Write-Host "Running: $gifCmd"

iex $gifCmd

Write-Host "Done. Outputs: $Output, $gif" -ForegroundColor Green
