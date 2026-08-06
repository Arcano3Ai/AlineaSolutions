# Script de Despliegue Automatizado para Alinea a Google Cloud Run
param (
    [string]$ProjectID = "fluted-dynamo-483120-h8",
    [string]$Region = "us-central1",
    [string]$ServiceName = "alinea-classifier"
)

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   INICIANDO DESPLIEGUE DE ALINEA EN GOOGLE CLOUD   " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Verificar si gcloud CLI está instalado
$gcloudCheck = Get-Command gcloud -ErrorAction SilentlyContinue
if (-not $gcloudCheck) {
    Write-Error "La herramienta 'gcloud' (Google Cloud SDK) no está instalada o no se encuentra en el PATH. Instálala antes de continuar."
    exit 1
}

# 2. Configurar el proyecto activo en gcloud
Write-Host "1. Configurando Proyecto de Google Cloud: $ProjectID..." -ForegroundColor Yellow
gcloud config set project $ProjectID

# 3. Habilitar las APIs necesarias en GCP
Write-Host "2. Habilitando APIs requeridas (Cloud Run, Cloud Build, Secret Manager)..." -ForegroundColor Yellow
gcloud services enable run.googleapis.com build.googleapis.com secretmanager.googleapis.com storage.googleapis.com

# 4. Compilar la imagen en Cloud Build (evita requerir Docker local)
Write-Host "3. Compilando y subiendo contenedor a Google Artifact Registry..." -ForegroundColor Yellow
gcloud builds submit --tag gcr.io/$ProjectID/$ServiceName

# 5. Desplegar en Google Cloud Run
Write-Host "4. Desplegando el contenedor en Google Cloud Run (Serverless)..." -ForegroundColor Yellow
gcloud run deploy $ServiceName `
    --image gcr.io/$ProjectID/$ServiceName `
    --platform managed `
    --region $Region `
    --allow-unauthenticated `
    --set-env-vars "FLASK_ENV=production,GOOGLE_CLOUD_PROJECT=$ProjectID"

Write-Host "==========================================================" -ForegroundColor Green
Write-Host "      DESPLIEGUE COMPLETADO CON ÉXITO EN CLOUD RUN        " -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green
