#! /usr/bin/env python3

# get the version from the pyproject.toml file
import tomllib
import asyncio

with open("pyproject.toml", "rb") as f:
    pyproject = tomllib.load(f)

version = pyproject["project"]["version"]

container_image = f"ghcr.io/jingkaihe/opsmate:{version}"


async def gen_help(subcommand: str):
    import subprocess

    try:
        # Run the command and capture the output asynchronously
        process = await asyncio.create_subprocess_shell(
            f"docker run --rm {container_image} {subcommand} --help",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise subprocess.CalledProcessError(
                process.returncode, f"{subcommand} --help", stderr
            )

        return stdout.decode().strip()
    except subprocess.CalledProcessError as e:
        raise e


async def main():
    cmds = [
        "chat",
        "db-migrate",
        "db-revisions",
        "db-rollback",
        "ingest-prometheus-metrics-metadata",
        "ingest",
        "install",
        "list-contexts",
        "list-models",
        "list-tools",
        "list-runtimes",
        "reset",
        "run",
        "schedule-embeddings-reindex",
        "serve",
        "solve",
        "uninstall",
        "worker",
    ]

    help_texts = {}
    lock = asyncio.Lock()
    # Process all commands concurrently
    tasks = [process_command(cmd, lock, help_texts) for cmd in cmds]
    await asyncio.gather(*tasks)

    for cmd, help_text in help_texts.items():
        # Update the docs in `docs/CLI/` specifically the `## OPTIONS` section
        with open(f"docs/CLI/{cmd}.md", "r") as f:
            content = f.read()

        # Format the help text as markdown with proper code block
        formatted_help = f"\n```\n{help_text}\n```\n"

        # Find the OPTIONS section and replace its content
        import re

        if "## OPTIONS" in content:
            # Replace everything between ## OPTIONS and the next heading (or end of file)
            pattern = r"(## OPTIONS\n)(?:.*?)(?=\n## |\Z)"
            updated_content = re.sub(
                pattern, r"\1" + formatted_help, content, flags=re.DOTALL
            )
        else:
            # If OPTIONS section doesn't exist, append it
            updated_content = content + f"\n## OPTIONS\n{formatted_help}"

        with open(f"docs/CLI/{cmd}.md", "w") as f:
            f.write(updated_content)


async def process_command(cmd, lock, help_texts):
    async with lock:
        help_texts[cmd] = await gen_help(cmd)


if __name__ == "__main__":
    asyncio.run(main())
