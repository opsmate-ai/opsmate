This cookbook demonstrates how to use the Kubernetes runtime to interact with a Kubernetes pod.

## Prerequisites

- A Kubernetes cluster
- Opsmate installed on your machine


## Interact with a pre-existing Kubernetes pod

First let's create a pod in the Kubernetes cluster.

```bash
kubectl run -i --tty --rm debug --image=alpine -- sh
```

Now that we have a pod running, we can interact with it using Opsmate's Kubernetes runtime.

```bash
opsmate run -nt --runtime
k8s --runtime-k8s-pod debug "what's the distro of this container?" --tools ShellCommand
The container is running Alpine Linux, version 3.21.3.
```

Here are some of the common configuration options for the Kubernetes runtime:

```bash
  --runtime-k8s-shell TEXT        Set shell_cmd (env: RUNTIME_K8S_SHELL)
  --runtime-k8s-container TEXT    Name of the container of the pod, if not
  --runtime-k8s-pod TEXT          Set pod_name (env: RUNTIME_K8S_POD)
  --runtime-k8s-namespace TEXT    Set namespace (env: RUNTIME_K8S_NAMESPACE)
```

## See Also

- [Docker Runtime](docker-runtime.md)
- [SSH Runtime](manage-vms.md)
