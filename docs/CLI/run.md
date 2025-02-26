`opsmate run` executes a command and returns the output.

## Options

```
Options:
  -m, --model TEXT    OpenAI model to use. To list models available please run
                      the list-models command.  [default: gpt-4o]
  -c, --context TEXT  Context to be added to the prompt. Run the list-contexts
                      command to see all the contexts available.  [default:
                      cli]
  --tools TEXT        Comma separated list of tools to use
  -r, --review        Review and edit commands before execution
  --help              Show this message and exit.
```

## Usage

### Simple command
This is the most basic usage of `opsmate run`, it will execute the command based on the natural language instruction.

```
opsmate run "what's the linux distribution?"
```

### Execute command with review

By default the command will be executed immediately without any review. You can use the `--review` flag to review the command before execution. Instead of a "yes" or "no" confirmation, you will be able to edit the command before execution.

```
opsmate run "what's the linux distribution?" --review
...
Edit the command if needed, then press Enter to execute: !cancel - Cancel the command
Press Enter or edit the command (cat /etc/os-release): cat /etc/os-release | grep '^PRETTY_NAME'
...
```

### Execute command with different model

By default, the model is `gpt-4o`, but you can use a different model for command execution.

```
opsmate run "what's the linux distribution?" -m gpt-4o-mini
```

### Execute command with different context

Context is represents a collection of tools and prompts. By default, the context is `cli`, but you can create your own context or use the predefined contexts as shown below.

```
opsmate run "how many pods are running in the cluster?" -c k8s
```

### Execute command with different tools

You can also use the `--tools` or `-t` flag to use a different tools. The tools are comma separated values.
The example below shows how to use the `HtmlToText` tool to get top 10 news on the hacker news.

```
opsmate run "find me top 10 news on the hacker news" --tools HtmlToText

...
  1 The FFT Strikes Back: An Efficient Alternative to Self-Attention - 27 points
  2 Telescope – an open-source web-based log viewer for logs stored in ClickHouse - 47 points
  3 DeepGEMM: clean and efficient FP8 GEMM kernels with fine-grained scaling - 316 points
  4 I Went to SQL Injection Court - 898 points
  5 Page is under construction: A love letter to the personal website - 97 points
  6 Iterated Log Coding - 44 points
  7 Hyperspace - 705 points
  8 Part two of Grant Sanderson's video with Terry Tao on the cosmic distance ladder - 290 points
  9 A compendium of "open-source" licenses - 7 points
 10 Material Theme has been pulled from VS Code's marketplace - 189 points

```
