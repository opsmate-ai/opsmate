`opsmate list-contexts` lists all the contexts available.

## USAGE

```bash
opsmate list-contexts

                                    Contexts
┏━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Context   ┃ Description                                                       ┃
┡━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ cli       │ General purpose context for solving problems on the command line. │
│ k8s       │ Kubernetes context for solving problems on Kubernetes.            │
│ terraform │ Terraform context for running Terraform based IaC commands.       │
└───────────┴───────────────────────────────────────────────────────────────────┘
```

Currently there is no way to add custom contexts from the CLI. This is a feature that is coming soon.
