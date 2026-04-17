while ($true) {
    Clear-Host
    Set-Location D:\Athenaeum_Project\library_api

    & .\venv312\Scripts\Activate.ps1

    Write-Host "Starting server... (CTRL+C to stop)"

    $proc = Start-Process python `
        -ArgumentList "-m uvicorn app.main:app --loop asyncio" `
        -NoNewWindow `
        -PassThru

    Wait-Process -Id $proc.Id

    Write-Host ""
    Write-Host "Server stopped. Press any key to restart..."
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
}