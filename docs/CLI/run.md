`opsmate run` executes a command and returns the output.

## OPTIONS

```bash
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

## USAGE

### Simple command
This is the most basic usage of `opsmate run`, it will execute the command based on the natural language instruction.

```bash
opsmate run "what's the linux distribution?"
```

### Execute command with review

By default the command will be executed immediately without any review. You can use the `--review` flag to review the command before execution. Instead of a "yes" or "no" confirmation, you will be able to edit the command before execution.

```bash
opsmate run "what's the linux distribution?" --review
...
Edit the command if needed, then press Enter to execute: !cancel - Cancel the command
Press Enter or edit the command (cat /etc/os-release): cat /etc/os-release | grep '^PRETTY_NAME'
...
```

### Execute command with different model

By default, the model is `gpt-4o`, but you can use a different model for command execution.

```bash
opsmate run "what's the linux distribution?" -m gpt-4o-mini
```

### Execute command with different context

Context is represents a collection of tools and prompts. By default, the context is `cli`, but you can create your own context or use the predefined contexts as shown below.

```bash
opsmate run "how many pods are running in the cluster?" -c k8s
```

### Execute command with different tools

You can also use the `--tools` or `-t` flag to use a different tools. The tools are comma separated values.
The example below shows how to use the `HtmlToText` tool to get top 10 news on the hacker news.

```bash
opsmate run "find me top 10 news on the hacker news" --tools HtmlToText

...
Here are the top 10 stories on Hacker News:

  1 The FFT Strikes Back: An Efficient Alternative to Self-Attention
     • Points: 30, Comments: 4
     • Posted by: iNic, 1 hour ago
  2 Telescope – an open-source web-based log viewer for logs stored in ClickHouse
     • Points: 48, Comments: 17
     • Posted by: r0b3r4, 2 hours ago
  3 DeepGEMM: clean and efficient FP8 GEMM kernels with fine-grained scaling
     • Points: 316, Comments: 59
     • Posted by: mfiguiere, 10 hours ago
  4 I Went to SQL Injection Court
     • Points: 899, Comments: 352
     • Posted by: mrkurt, 16 hours ago
  5 Page is under construction: A love letter to the personal website
     • Points: 100, Comments: 36
     • Posted by: spzb, 5 hours ago
  6 Iterated Log Coding
     • Points: 44, Comments: 14
     • Posted by: snarkconjecture, 3 hours ago
  7 Hyperspace
     • Points: 705, Comments: 369
     • Posted by: tobr, 19 hours ago
  8 Part two of Grant Sanderson's video with Terry Tao on the cosmic distance ladder
     • Points: 291, Comments: 46
     • Posted by: ColinWright, 16 hours ago
  9 Material Theme has been pulled from VS Code's marketplace
     • Points: 190, Comments: 144
     • Posted by: Inityx, 11 hours ago
 10 Terence Tao – Machine-Assisted Proofs [video]
     • Points: 78, Comments: 7
     • Posted by: ipnon, 9 hours ago
```

### SEE ALSO

- [opsmate solve](./solve.md)
- [opsmate chat](./chat.md)
- [opsmate list-contexts](./list-contexts.md)
- [opsmate list-tools](./list-tools.md)
- [opsmate list-models](./list-models.md)
