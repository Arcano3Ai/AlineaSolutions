# Script para renombrar archivos con caracteres especiales (tildes, ñ, etc.)
# que gcloud no puede procesar en Windows al hacer builds submit.
# Solo renombra los caracteres problemáticos, preserva el ID y el sentido del nombre.

$replacements = @{
    'á' = 'a'; 'é' = 'e'; 'í' = 'i'; 'ó' = 'o'; 'ú' = 'u'; 'ü' = 'u'
    'Á' = 'A'; 'É' = 'E'; 'Í' = 'I'; 'Ó' = 'O'; 'Ú' = 'U'; 'Ü' = 'U'
    'ñ' = 'n'; 'Ñ' = 'N'
    '¿' = ''; '¡' = ''
    # Caracteres que Windows/gcloud tampoco maneja bien en rutas
    '°' = 'o'
}

$targetDir = Join-Path $PSScriptRoot "conocimiento"
$files = Get-ChildItem -Path $targetDir -Recurse -File

$renamed = 0
$skipped = 0
$errors  = 0

foreach ($file in $files) {
    $originalName = $file.Name
    $newName = $originalName

    foreach ($key in $replacements.Keys) {
        $newName = $newName.Replace($key, $replacements[$key])
    }

    if ($newName -ne $originalName) {
        $newPath = Join-Path $file.DirectoryName $newName
        try {
            # Si ya existe un archivo con el nombre destino, no lo sobreescribimos
            if (Test-Path $newPath) {
                Write-Warning "  Ya existe: '$newName' — omitiendo '$originalName'"
                $skipped++
            } else {
                Rename-Item -Path $file.FullName -NewName $newName -ErrorAction Stop
                Write-Host "  Renombrado: '$originalName'" -ForegroundColor Green
                Write-Host "          -> '$newName'" -ForegroundColor Cyan
                $renamed++
            }
        } catch {
            Write-Error "  ERROR renombrando '$($file.FullName)': $_"
            $errors++
        }
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Yellow
Write-Host " Renombrados : $renamed" -ForegroundColor Green
Write-Host " Omitidos    : $skipped" -ForegroundColor Yellow
Write-Host " Errores     : $errors"  -ForegroundColor Red
Write-Host "========================================" -ForegroundColor Yellow
Write-Host "Listo. Ahora puedes ejecutar el deploy." -ForegroundColor Cyan
