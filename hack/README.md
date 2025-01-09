# Payment Service

Payment service is a service that is used to process payments.

Code can be found in `hack/app.py`. Containerisation is done in `hack/Dockerfile`.

The deployment can be found in `hack/deploy.yml`.

## Health check

The health check for the payment service is performed by the `readinessProbe` and `livenessProbe` in the deployment.

Health check is performed by checking the `/status` endpoint instead of the conventional `healthz` or `/healthz` endpoints.

## Deploy

```bash
kubectl apply -f hack/deploy.yml
```
