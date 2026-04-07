# Kubernetes RBAC Configuration

This directory contains Role-Based Access Control (RBAC) manifests for the DevOps K8s Platform. These manifests implement the principle of least privilege by creating service accounts with minimal required permissions for deployment and monitoring operations.

## Overview

The platform uses two separate service accounts:

1. **devops-platform-deployer**: Used for deployment operations
2. **devops-platform-monitor**: Used for monitoring operations (read-only)

## Service Accounts

### Deployer Service Account
- **Name**: `devops-platform-deployer`
- **Purpose**: Deploy and manage application resources
- **Permissions**: Create, read, update, and delete application resources

### Monitor Service Account
- **Name**: `devops-platform-monitor`
- **Purpose**: Monitor application health and collect metrics
- **Permissions**: Read-only access to pods, logs, events, and metrics

## Roles and Permissions

### Deployer Role (`devops-platform-deployer-role`)

**Namespace-scoped permissions:**
- **ConfigMaps**: get, list, create, update, patch, delete
- **Secrets**: get, list, create, update, patch, delete
- **PersistentVolumeClaims**: get, list, create, delete
- **Services**: get, list, create, update, patch, delete
- **Pods**: get, list, watch (read-only for health checks)
- **Pod Logs**: get, list (read-only for monitoring)
- **Events**: get, list, watch (read-only for health checks)
- **Deployments**: get, list, create, update, patch, delete
- **StatefulSets**: get, list, create, update, patch, delete
- **ReplicaSets**: get, list, watch (read-only for status)
- **Ingress**: get, list, create, update, patch, delete

**Cluster-scoped permissions:**
- **Namespaces**: get, list (read-only for validation)
- **Nodes**: get, list (read-only for health checks)

### Monitor Role (`devops-platform-monitor-role`)

**Namespace-scoped permissions (all read-only):**
- **Pods**: get, list, watch
- **Pod Logs**: get, list
- **Pod Status**: get, list
- **Services**: get, list, watch
- **Events**: get, list, watch
- **ConfigMaps**: get, list
- **Deployments**: get, list, watch
- **Deployment Status**: get, list
- **StatefulSets**: get, list, watch
- **StatefulSet Status**: get, list
- **ReplicaSets**: get, list, watch
- **PersistentVolumeClaims**: get, list

**Cluster-scoped permissions (all read-only):**
- **Nodes**: get, list
- **Node Stats**: get, list
- **Namespaces**: get, list

## Installation

### Apply RBAC Manifests

To install the RBAC configuration in your Kubernetes cluster:

```bash
# Apply all RBAC manifests
kubectl apply -f backend/k8s/rbac/

# Or apply individually in order:
kubectl apply -f backend/k8s/rbac/service-account.yaml
kubectl apply -f backend/k8s/rbac/deployer-role.yaml
kubectl apply -f backend/k8s/rbac/monitor-role.yaml
kubectl apply -f backend/k8s/rbac/role-bindings.yaml
```

### Verify Installation

```bash
# Check service accounts
kubectl get serviceaccounts -n default | grep devops-platform

# Check roles
kubectl get roles -n default | grep devops-platform
kubectl get clusterroles | grep devops-platform

# Check role bindings
kubectl get rolebindings -n default | grep devops-platform
kubectl get clusterrolebindings | grep devops-platform
```

### Get Service Account Token

To use the service account from outside the cluster, you need to create a token:

```bash
# For Kubernetes 1.24+, create a token manually
kubectl create token devops-platform-deployer -n default --duration=8760h

# Or create a long-lived token secret (for older versions)
kubectl apply -f - <<EOF
apiVersion: v1
kind: Secret
metadata:
  name: devops-platform-deployer-token
  namespace: default
  annotations:
    kubernetes.io/service-account.name: devops-platform-deployer
type: kubernetes.io/service-account-token
EOF

# Get the token
kubectl get secret devops-platform-deployer-token -n default -o jsonpath='{.data.token}' | base64 -d
```

## Configuration in DeployerService

The DeployerService should be configured to use the service account token:

```python
from kubernetes import client, config

# Load configuration with service account token
configuration = client.Configuration()
configuration.host = "https://your-cluster-api-server"
configuration.api_key = {"authorization": "Bearer " + service_account_token}
configuration.verify_ssl = True  # Set to False for testing only

# Create API client
api_client = client.ApiClient(configuration)
core_v1 = client.CoreV1Api(api_client)
apps_v1 = client.AppsV1Api(api_client)
```

## Security Considerations

### Principle of Least Privilege
- The deployer service account has only the permissions required for deployment operations
- The monitor service account has read-only access only
- No cluster-admin or elevated privileges are granted

### Namespace Isolation
- Roles are namespace-scoped where possible
- ClusterRoles are used only for operations that require cluster-wide access
- Consider creating separate service accounts per namespace for multi-tenant deployments

### Token Management
- Service account tokens should be stored securely (encrypted at rest)
- Tokens should be rotated regularly
- Use short-lived tokens when possible (Kubernetes 1.24+)

### Audit and Monitoring
- Enable Kubernetes audit logging to track service account usage
- Monitor for unauthorized access attempts
- Review and update permissions regularly

## Multi-Namespace Deployment

To deploy applications to multiple namespaces, you have two options:

### Option 1: Create RoleBindings in Each Namespace

```bash
# Create role binding in a specific namespace
kubectl create rolebinding devops-platform-deployer-binding \
  --role=devops-platform-deployer-role \
  --serviceaccount=default:devops-platform-deployer \
  -n target-namespace
```

### Option 2: Use ClusterRole and ClusterRoleBinding

For multi-namespace deployments, consider converting the namespace-scoped Role to a ClusterRole and using ClusterRoleBinding. However, this grants broader permissions and should be carefully evaluated.

## Testing RBAC

### Test Deployer Permissions

```bash
# Test as deployer service account
kubectl auth can-i create deployments --as=system:serviceaccount:default:devops-platform-deployer -n default
# Should return: yes

kubectl auth can-i delete pods --as=system:serviceaccount:default:devops-platform-deployer -n default
# Should return: no (deployer can't delete pods directly)
```

### Test Monitor Permissions

```bash
# Test as monitor service account
kubectl auth can-i get pods --as=system:serviceaccount:default:devops-platform-monitor -n default
# Should return: yes

kubectl auth can-i create deployments --as=system:serviceaccount:default:devops-platform-monitor -n default
# Should return: no (monitor is read-only)
```

## Troubleshooting

### Permission Denied Errors

If you encounter permission denied errors:

1. Verify the service account exists:
   ```bash
   kubectl get sa devops-platform-deployer -n default
   ```

2. Check role bindings:
   ```bash
   kubectl get rolebinding devops-platform-deployer-binding -n default -o yaml
   ```

3. Test specific permissions:
   ```bash
   kubectl auth can-i <verb> <resource> --as=system:serviceaccount:default:devops-platform-deployer -n default
   ```

4. Check audit logs for detailed error messages

### Token Issues

If authentication fails:

1. Verify token is valid and not expired
2. Check cluster API server URL is correct
3. Verify SSL/TLS configuration
4. Ensure token has correct format (Bearer token)

## Cleanup

To remove the RBAC configuration:

```bash
# Delete all RBAC resources
kubectl delete -f backend/k8s/rbac/

# Or delete individually
kubectl delete clusterrolebinding devops-platform-deployer-cluster-binding
kubectl delete clusterrolebinding devops-platform-monitor-cluster-binding
kubectl delete rolebinding devops-platform-deployer-binding -n default
kubectl delete rolebinding devops-platform-monitor-binding -n default
kubectl delete clusterrole devops-platform-deployer-cluster-role
kubectl delete clusterrole devops-platform-monitor-cluster-role
kubectl delete role devops-platform-deployer-role -n default
kubectl delete role devops-platform-monitor-role -n default
kubectl delete sa devops-platform-deployer -n default
kubectl delete sa devops-platform-monitor -n default
```

## References

- [Kubernetes RBAC Documentation](https://kubernetes.io/docs/reference/access-authn-authz/rbac/)
- [Using RBAC Authorization](https://kubernetes.io/docs/reference/access-authn-authz/rbac/)
- [Service Account Tokens](https://kubernetes.io/docs/reference/access-authn-authz/service-accounts-admin/)
