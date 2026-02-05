# Manifest Export Implementation

## Overview

The Manifest Export Service provides functionality to export Kubernetes manifests from a deployment as a downloadable ZIP archive. Manifests are organized by resource type into separate folders for easy management.

**Requirements:** 13.2, 13.3, 13.4

## Implementation Details

### API Endpoint

**GET /api/export/{deployment_id}**

Exports all Kubernetes manifests from a deployment as a ZIP file.

**Parameters:**
- `deployment_id` (path): UUID of the deployment to export

**Headers:**
- `Authorization`: Bearer token for authentication

**Response:**
- Content-Type: `application/zip`
- Content-Disposition: `attachment; filename=k8s-manifests-{deployment_name}-{deployment_id}.zip`

### ZIP Archive Structure

The exported ZIP file contains:

```
k8s-manifests-{deployment_name}-{deployment_id}.zip
├── README.md                           # Usage instructions
├── deployments/
│   ├── web-deployment.yaml
│   └── worker-deployment.yaml
├── services/
│   ├── web-service.yaml
│   └── api-service.yaml
├── configmaps/
│   └── app-config.yaml
├── secrets/
│   └── db-credentials.yaml
├── persistentvolumeclaims/
│   └── data-pvc.yaml
└── ingresses/
    └── web-ingress.yaml
```

### Supported Resource Types

The service organizes manifests into the following folders:

- `deployments/` - Deployment resources
- `services/` - Service resources
- `configmaps/` - ConfigMap resources
- `secrets/` - Secret resources
- `persistentvolumeclaims/` - PersistentVolumeClaim resources
- `ingresses/` - Ingress resources
- `statefulsets/` - StatefulSet resources
- `daemonsets/` - DaemonSet resources
- `jobs/` - Job resources
- `cronjobs/` - CronJob resources
- `namespaces/` - Namespace resources
- `serviceaccounts/` - ServiceAccount resources
- `roles/` - Role resources
- `rolebindings/` - RoleBinding resources
- `clusterroles/` - ClusterRole resources
- `clusterrolebindings/` - ClusterRoleBinding resources
- `other/` - Other resource types

## Usage Examples

### Python Example

```python
import requests

# Authentication
token = "your-jwt-token"
headers = {"Authorization": f"Bearer {token}"}

# Export manifests
deployment_id = "123e4567-e89b-12d3-a456-426614174000"
response = requests.get(
    f"http://localhost:8000/api/export/{deployment_id}",
    headers=headers
)

# Save ZIP file
if response.status_code == 200:
    with open("manifests.zip", "wb") as f:
        f.write(response.content)
    print("Manifests exported successfully!")
else:
    print(f"Error: {response.json()}")
```

### cURL Example

```bash
# Export manifests
curl -X GET \
  "http://localhost:8000/api/export/123e4567-e89b-12d3-a456-426614174000" \
  -H "Authorization: Bearer your-jwt-token" \
  -o manifests.zip

# Extract and apply
unzip manifests.zip -d k8s-manifests
cd k8s-manifests
kubectl apply -R -f .
```

### JavaScript/TypeScript Example

```typescript
async function exportManifests(deploymentId: string, token: string) {
  const response = await fetch(
    `http://localhost:8000/api/export/${deploymentId}`,
    {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    }
  );

  if (response.ok) {
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `manifests-${deploymentId}.zip`;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  } else {
    const error = await response.json();
    console.error('Export failed:', error);
  }
}
```

## Error Handling

### 404 Not Found
Deployment does not exist or user does not have access:
```json
{
  "detail": "Deployment {deployment_id} not found or not accessible"
}
```

### 400 Bad Request
Deployment has no manifests to export:
```json
{
  "detail": "Deployment has no manifests to export"
}
```

### 401 Unauthorized
Missing or invalid authentication token:
```json
{
  "detail": "Not authenticated"
}
```

### 500 Internal Server Error
Server error during export:
```json
{
  "detail": "Failed to export manifests: {error_message}"
}
```

## Security Considerations

1. **Authentication Required**: All export requests require valid JWT authentication
2. **User Isolation**: Users can only export their own deployments
3. **Data Validation**: Deployment ID is validated as UUID format
4. **Resource Access Control**: Database queries filter by user_id to prevent unauthorized access

## Implementation Components

### Router (`backend/app/routers/export.py`)

The export router provides:
- `GET /api/export/{deployment_id}` endpoint
- Manifest organization by resource type
- ZIP archive creation
- Streaming response for efficient file download

### Helper Functions

**`organize_manifests_by_type(manifests)`**
- Groups manifests by Kubernetes resource kind
- Maps kinds to folder names (pluralized)
- Returns dictionary of folder → manifests

**`create_zip_archive(manifests)`**
- Creates in-memory ZIP file
- Organizes manifests into folders
- Adds README with usage instructions
- Returns BytesIO buffer

## Testing

Comprehensive test suite in `backend/tests/test_export_api.py`:

- ✅ Successful export with multiple manifest types
- ✅ Export with non-existent deployment (404)
- ✅ Export with empty deployment (400)
- ✅ Unauthorized access (401)
- ✅ Cross-user access prevention (404)
- ✅ Proper manifest organization by type
- ✅ Multiple resource type handling

Run tests:
```bash
pytest backend/tests/test_export_api.py -v
```

## Integration with Frontend

The frontend can integrate the export functionality:

1. Add "Export Manifests" button to deployment dashboard
2. Call export endpoint with deployment ID
3. Trigger browser download of ZIP file
4. Display success/error messages

Example integration in React:

```typescript
const handleExport = async () => {
  try {
    const response = await api.exportManifests(deploymentId);
    // Browser will automatically download the file
    toast.success('Manifests exported successfully!');
  } catch (error) {
    toast.error('Failed to export manifests');
  }
};

<Button onClick={handleExport}>
  <Download className="mr-2" />
  Export Manifests
</Button>
```

## Future Enhancements

Potential improvements:
- Export format options (ZIP, tar.gz)
- Selective manifest export (choose specific resources)
- Export with Kustomize structure
- Export with Helm chart structure
- Include deployment metadata in export
- Export history/versioning

## Related Documentation

- [Deployment API](./DEPLOYER_SERVICE_IMPLEMENTATION.md)
- [Manifest Editor](../../frontend/docs/MANIFEST_EDITOR.md)
- [Requirements Document](../../.kiro/specs/devops-k8s-platform/requirements.md)
