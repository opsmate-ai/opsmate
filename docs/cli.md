# CLI

This documentation highlights some of the most common use cases of Opsmate CLI tools.

## Natural Language CLI run

One of the most simple use case of Opsmate is to run commands using natural language. This comes handy when you need to run a command that you don't know/remember the exact instruction.

```bash
$ opsmate run "what's the gpu of the vm"
                                                        Command
# Check the GPU installed on the VM using lspci command and filter for VGA or compatible graphics device.
lspci | grep -i 'vga\|3d\|2d'


                                                        Output
04:00.0 VGA compatible controller: Red Hat, Inc. Virtio 1.0 GPU (rev 01)

The VM is using a VGA compatible controller with a Red Hat, Inc. Virtio 1.0 GPU (rev 01).
```

## Advanced reasoning
A more advanced use case is to leverage Opsmate to perform reasoning and problem solving of production issues via using the `solve` command as you can see in the following example. Like a human SRE, Opsmate can make mistakes but with the advanced reasoning ability it can reflect on its mistakes and correct itself.

```bash
opsmate solve "what's the k8s distro of the current context"

Thought process
Thought: To determine the Kubernetes distribution of the current context, I need to access the Kubernetes configuration and context details.
Action: Run the command kubectl version --short or check the Kubernetes configuration using kubectl config current-context to get information about the server and its version.

...


Output
 error: unknown flag: --short
 See 'kubectl version --help' for usage.

...

Thought: I need to run a valid command to get cluster details without the --short option.
Action: Run kubectl version to get the full version details which might give us clues about the distribution in use.
...

Answer: The Kubernetes distribution of the current context is K3s, as indicated by the +k3s1 suffix in the server version output from kubectl version.
```

## Chat with Opsmate
To have the human-in-the-loop experience you can run

```bash
opsmate chat
```

## API and Web UI

To serve the Opsmate with a web interface and API you can run the following command:

```bash
opsmate serve
```

You can access the web interface at [http://localhost:8080](http://localhost:8080).

API documentation is available at [http://localhost:8080/api/docs](http://localhost:8080/api/docs).
