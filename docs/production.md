# Production

This documentation highlights how to run Opsmate in production environment.

## Why bother?

`Opsmate` can be used as a [command line tool](./CLI/index.md) standalone however it comes with a few limitations:

- Every local workstation is a snowflake in its own way, thus it's hard to have a consistent experience across different machines.
- Some of the production environments access are simply not available from the local workstation.
- People cannot collaborate on a local workstation.

To address these issues, we also provide a `opsmate-operator` that can run `Opsmate` on demand in a Kubernetes cluster.

## Key features

Here are some of the key features of `opsmate-operator`:

- Manage the Opsmate environment via a `EnvironmentBuild` CRD.
- `Opsmate` can be scheduled on demand via a `Task` CRD.
- Each of the `Opsmate` task comes with a dedicated secured HTTPS endpoint and web UI, run inside a dedicated pod.
- `Opsmate` environment builds and tasks are scoped by the namespace thus support multi-tenancy.
- The task comes with a `TTL` (time to live) thus it will be automatically garbage collected after the TTL expires. By doing so we avoid resource waste.
- An API-server to allow you to manage the `Opsmate` environment and tasks.

## How to install the operator

Here is an example of how to install the operator using [Terraform](https://www.terraform.io/) and [Helm](https://helm.sh/).
```terraform
# Where you install the operator
resource "kubernetes_namespace" "opsmate_operator" {
  metadata {
    name = "opsmate-operator"
  }
}

resource "helm_release" "opsmate_operator" {
  name             = "opsmate-operator"
  repository       = "oci://ghcr.io/jingkaihe/opsmate-operator"
  chart            = "opsmate-operator"
  version          = "0.1.4"
  namespace        = kubernetes_namespace.opsmate_operator.metadata[0].name
  create_namespace = false
  max_history      = 3

  set {
    name  = "installCRDs"
    value = "true"
  }

  values = [
    yamlencode({
      controllerManager = {
        fullnameOverride = "opsmate-operator"
        manager = {
          image = {
            repository = "ghcr.io/jingkaihe/opsmate-controller-manager"
            tag        = "0.1.4.alpha2"
          }
        }
      }
    }),
  ]
}
```

## Environment Build

Opsmate Environment Build is a CRD (Custom Resource Definition) that defines the environment that will be used to run the `Opsmate` task.

The following example we:

- Create a new namespace `opsmate-workspace`
- Create a new cluster role `opsmate-cluster-reader` which is bound to the `opsmate-cluster-reader` service account.
- Create a new `environmentBuild` called `cluster-reader` which will be used as a template for running the `Opsmate` task.

The `environmentBuild` is composed of:

- A `opsmate` container that runs as a Web UI and API server.
- A `worker` container that is responsible for running background heavy-lifting tasks such as ingesting the knowledge base and embedding into the vector database.
- The `opsmate` and the `worker` containers shared the same volume for storing the sqlite database and the vector database.

<details><summary>Click to show opsmate-cluster-reader ClusterRole</summary>

```yaml
---
# cluster reader role
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: opsmate-cluster-reader
rules:
- apiGroups: [""]  # Core API group
  resources:
  - nodes
  - namespaces
  - pods
  - services
  - configmaps
  - secrets
  - persistentvolumes
  - persistentvolumeclaims
  - events
  verbs:
  - get
  - list
  - watch
- apiGroups: ["apps"]  # Apps API group
  resources:
  - deployments
  - daemonsets
  - statefulsets
  - replicasets
  verbs:
  - get
  - list
  - watch
- apiGroups: ["batch"]  # Batch API group
  resources:
  - jobs
  - cronjobs
  verbs:
  - get
  - list
  - watch
- apiGroups: ["networking.k8s.io"]  # Networking API group
  resources:
  - ingresses
  - networkpolicies
  verbs:
  - get
  - list
  - watch
- apiGroups: ["storage.k8s.io"]  # Storage API group
  resources:
  - storageclasses
  verbs:
  - get
  - list
  - watch
```

</details>

```yaml
---
apiVersion: v1
kind: Namespace
metadata:
  name: opsmate-workspace
---
# service account for cluster reader
apiVersion: v1
kind: ServiceAccount
metadata:
  name: opsmate-cluster-reader
  namespace: opsmate-workspace
---
# role binding for cluster reader
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: opsmate-cluster-reader
subjects:
- kind: ServiceAccount
  name: opsmate-cluster-reader
  namespace: opsmate-workspace
roleRef:
  kind: ClusterRole
  name: opsmate-cluster-reader
---
# configmap for opsmate task
apiVersion: v1
kind: ConfigMap
metadata:
  name: opsmate-config
  namespace: opsmate-workspace
data:
  OPSMATE_DB_URL: sqlite:////var/opsmate/opsmate.sqlite
  EMBEDDINGS_DB_PATH: /var/opsmate/embedding
  GITHUB_EMBEDDINGS_CONFIG: |
    {
      "jingkaihe/opsmate": "**/*.md"
    }
---
# cluster reader environment build
apiVersion: sre.opsmate.io/v1alpha1
kind: EnvironmentBuild
metadata:
  name: cluster-reader
  namespace: opsmate-workspace
spec:
  podTemplate:
    spec:
      serviceAccountName: opsmate-cluster-reader
      initContainers:
        - name: opsmate-db-migrate
          image: ghcr.io/jingkaihe/opsmate:0.1.45a0
          args:
            - db-migrate
          envFrom:
            - configMapRef:
                name: opsmate-config
          volumeMounts:
            - name: opsmate-vol
              mountPath: /var/opsmate
      containers:
        - name: opsmate
          image: ghcr.io/jingkaihe/opsmate:0.1.45a0
          ports:
            - containerPort: 8000
          envFrom:
            - secretRef:
                name: opsmate-secret
            - configMapRef:
                name: opsmate-config
          volumeMounts:
            - name: opsmate-vol
              mountPath: /var/opsmate
          args:
            - serve
            - --auto-migrate=false
        - name: worker
          image: ghcr.io/jingkaihe/opsmate:0.1.45a0
          envFrom:
            - secretRef:
                name: opsmate-secret
            - configMapRef:
                name: opsmate-config
          args:
            - worker
            - --auto-migrate=false
          volumeMounts:
            - name: opsmate-vol
              mountPath: /var/opsmate
      imagePullSecrets:
        - name: opsmate-workspace-image-pull-secret
      volumes:
      - name: opsmate-vol
        emptyDir:
          sizeLimit: 500Mi
  service:
    type: ClusterIP
    ports:
      - port: 80
        targetPort: 8000
  ingressTLS: true
  ingressTargetPort: 80
```

There are a few secrets that you will need to create:

* `OPENAI_API_KEY` - If you are using OpenAI as your LLM provider. Currently it is mandatory as we are using OpenAI's embedding API for embedding the knowledge base.
* `ANTHROPIC_API_KEY` - If you are using Anthropic as your LLM provider.
* `XAI_API_KEY` - If you are using xAI as your LLM provider.
* `GITHUB_TOKEN` - This is used for
  - Accessing the GitHub repository for loading knowledge base.
  - Used by Opsmate to to clone the repo, commit changes and raise PRs.

Here are the examples of how to create the secrets:
=== "Secret"
    ```yaml
    apiVersion: v1
    kind: Secret
    metadata:
      name: opsmate-secret
      namespace: opsmate-workspace
    type: Opaque
    data:
      OPENAI_API_KEY: <your-openai-api-key-base64-encoded>
      ANTHROPIC_API_KEY: <your-anthropic-api-key-base64-encoded>
      GITHUB_TOKEN: <your-github-token-base64-encoded>
    ```

=== "External Secret Manager"
    ```yaml
    ---
    apiVersion: external-secrets.io/v1beta1
    kind: SecretStore
    metadata:
      name: gcp-secret-store
      namespace: opsmate-workspace
    spec:
      provider:
        gcpsm:
          projectID: $YOUR_GCP_PROJECT_ID
    ---
    apiVersion: external-secrets.io/v1beta1
    kind: ExternalSecret
    metadata:
      name: opsmate-secret
      namespace: opsmate-workspace
    spec:
      refreshInterval: 1h
      secretStoreRef:
        kind: SecretStore
        name: gcp-secret-store
      target:
        name: opsmate-secret
        creationPolicy: Owner
      data:
        - secretKey: OPENAI_API_KEY
          remoteRef:
            key: opsmate-workspace-openai-key
        - secretKey: ANTHROPIC_API_KEY
          remoteRef:
            key: opsmate-workspace-anthropic-key
        - secretKey: GITHUB_TOKEN
          remoteRef:
            key: opsmate-workspace-github-token-ro
    ```

## Task

The task is a CRD that defines a workspace that will be used for tackling production problem.

Here is an example of a task:

```yaml
---
apiVersion: sre.opsmate.io/v1alpha1
kind: Task
metadata:
  name: investigator
  namespace: opsmate-workspace
spec:
  userID: anonymous
  environmentBuildName: cluster-reader
  description: "a opsmate task for investigating the cluster"
  context: "you are on a kubernetes cluster"
  domainName: "investigator.opsmate.your-corp.com"
  ingressAnnotations:
    external-dns.alpha.kubernetes.io/hostname: investigator.opsmate.your-corp.com
  ingressSecretName: opsmate-cert
```

In the example above we assume that you:

- Own the domain name `opsmate.your-corp.com`
- Can use [external-dns](https://github.com/kubernetes-sigs/external-dns) to manage the ingress for the domain name.
- Have a wildcard `*.opsmate.your-corp.com` certificate in the `opsmate-workspace` namespace managed by [cert-manager](https://cert-manager.io/). Notes the wildcard certificate can now be provisioned by [LetsEncrypt](https://letsencrypt.org/docs/faq/#does-let-s-encrypt-issue-wildcard-certificates).

After you create the task you can access the task via the following URL:

```bash
https://investigator.opsmate.your-corp.com?token=$(kubectl -n opsmate-workspace get task investigator -o jsonpath='{.status.token}')
```
