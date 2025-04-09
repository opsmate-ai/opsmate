This cookbook will guide you through how to interact with Docker container using Opsmate's docker runtime.

## Prerequisites

- Docker installed on your machine
- Opsmate installed on your machine

## Example 1: Interact with a pre-existing docker container

First thing first let's create a docker container running in the background.

```bash
docker run -d --name testbox --rm ubuntu:20.04 sleep infinity
```

Now with the container running, we can interact with it using Opsmate's docker runtime.

```bash
# -nt only prints out the answer
$ opsmate run -nt --shell-command-runtime docker --runtime-docker-container-name testbox "what is the os distro"
The OS distribution is Ubuntu 20.04.6 LTS (Focal Fossa).
```

You can also use [solve](../CLI/solve.md) and [chat](../CLI/chat.md) to interact with the container.

## Example 2: Interact with a docker container from docker-compose

[Docker Compose](https://docs.docker.com/compose/) is a tool for defining and running multi-container Docker applications. In conjunction with Opsmate's docker runtime, you can achieve goals such as:

- Executing exploratory experiments within a containerised environment.
- Use the containerised runtime as a workstation powered by AI, such as the [three-musketeers](https://3musketeers.pages.dev/) approach
- You need to use a containerised runtime to run complicated evaluation tasks, which otherwise is not feasible to run on your host space.

Let's say we have the following `docker-compose.yml` file:

```yaml
services:
  default:
    image: ubuntu:24.04
    init: true
    entrypoint: ["sleep", "infinity"]
  redis:
    image: redis:latest
```

To interact with the environment you can run:

```bash
opsmate chat --shell-command-runtime docker
```

By default it will auto detect the `docker-compose.yml` file in the current directory, and use the `default` service as the container to interact with.

You can also specify the `docker-compose.yml` file and the service you want to interact with:

```bash
# investigate the redis service
opsmate solve \
  --runtime docker \
  --runtime-docker-compose-file ./docker-compose.yml \
  --runtime-docker-service-name redis \
  "what are the name of the processes that are running, find it out using the /proc directory"
```

{{ asciinema("/assets/docker-compose-runtime.cast") }}

Here are some of the common configuration options for the docker runtime:

```bash
  --runtime-docker-service-name TEXT
  --runtime-docker-compose-file TEXT
                                  Path to the docker compose file (env:
                                  docker-compose.yml]
  --runtime-docker-shell TEXT     Set shell_cmd (env: RUNTIME_DOCKER_SHELL)
  --runtime-docker-container-name TEXT
```

## See Also

- [Kubernetes Runtime](k8s-runtime.md)
- [SSH Runtime](manage-vms.md)
