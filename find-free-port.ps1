param(
    [int]$StartPort = 3011,
    [int]$EndPort = 3099
)

$ErrorActionPreference = 'Stop'

if ($StartPort -lt 1024 -or $EndPort -gt 65535 -or $StartPort -gt $EndPort) {
    exit 1
}

for ($port = $StartPort; $port -le $EndPort; $port++) {
    $listener = $null
    try {
        # Bind all local interfaces so a service listening on 0.0.0.0 is also detected.
        $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Any, $port)
        $listener.Start()
        $listener.Stop()
        $listener = $null
        Write-Output $port
        exit 0
    } catch {
        if ($listener) {
            try { $listener.Stop() } catch {}
        }
    }
}

exit 2
