# Test script for API endpoints

$composeContent = @"
version: '3.8'

services:
  web:
    image: nginx:latest
    ports:
      - "80:80"
    environment:
      - NGINX_HOST=localhost
    networks:
      - frontend

  api:
    image: node:18-alpine
    ports:
      - "3000:3000"
    depends_on:
      - db
    networks:
      - frontend
      - backend

  db:
    image: postgres:15
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
    volumes:
      - db-data:/var/lib/postgresql/data
    networks:
      - backend

volumes:
  db-data:
    driver: local

networks:
  frontend:
    driver: bridge
  backend:
    driver: bridge
"@

$body = @{
    content = $composeContent
} | ConvertTo-Json

Write-Host "Testing /api/compose/upload endpoint..." -ForegroundColor Cyan

try {
    $response = Invoke-RestMethod -Uri "http://localhost:8000/api/compose/upload" `
        -Method Post `
        -ContentType "application/json" `
        -Body $body

    Write-Host "`nSuccess! Response:" -ForegroundColor Green
    $response | ConvertTo-Json -Depth 10

    Write-Host "`nValidation:" -ForegroundColor Yellow
    Write-Host "Valid: $($response.validation.valid)"
    Write-Host "Errors: $($response.validation.errors.Count)"

    Write-Host "`nStructure:" -ForegroundColor Yellow
    Write-Host "Services: $($response.structure.services.Count)"
    Write-Host "Volumes: $($response.structure.volumes.Count)"
    Write-Host "Networks: $($response.structure.networks.Count)"

    Write-Host "`nService Names:" -ForegroundColor Yellow
    foreach ($service in $response.structure.services) {
        Write-Host "  - $($service.name)"
    }

} catch {
    Write-Host "`nError:" -ForegroundColor Red
    Write-Host $_.Exception.Message
    Write-Host $_.ErrorDetails.Message
}
