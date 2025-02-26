`opsmate solve` solves a SRE/DevOps oriented task via reasoning.

Unlike most of the state-of-the-art LLMs models (e.g. o1-pro, deepseek R1) that scheming in the background and come back to you 1 minute later, OpsMate reasoning via actively interactive with the environment to gather information and trial and error to find the best solution. We believe short feedback loop is key to solve SRE/DevOps oriented tasks.

## OPTIONS

```bash
Usage: opsmate solve [OPTIONS] INSTRUCTION

  Solve a problem with the OpsMate.

Options:
  -m, --model TEXT        OpenAI model to use. To list models available please
                          run the list-models command.  [default: gpt-4o]
  -i, --max-iter INTEGER  Max number of iterations the AI assistant can reason
                          about  [default: 10]
  -c, --context TEXT      Context to be added to the prompt. Run the list-
                          contexts command to see all the contexts available.
                          [default: cli]
  --tools TEXT            Comma separated list of tools to use
  -r, --review            Review and edit commands before execution
  --help                  Show this message and exit.
```

## USAGE

### The most basic usage

In the example below, the OpsMate will reason about the problem and come up with a solution, going through the "thought-action-observation" loop.

```bash
opsmate solve "how many cores on the server?"
```

### Using a different model

Like the [`run` command](./run.md), you can use the `--model` option to use a different model.
```bash
opsmate solve "how many cores on the server?" -m grok-2-1212
```

### Increase the number of iterations

You can increase the number of iterations the OpsMate can reason about by using the `--max-iter` option for anything that requires long reasoning. There are a few things to bare in mind though:

- More iterations means more LLM tokens used. As the context window gets progressively larger over iterations, the cost will increase.
- In real-world use cases more iterations doesn't necessarily translate to better results. The common pattern we have observed is that with the current frontier LLMs, 10-15 iterations is the sweet spot. The longer the task, the more "confused" LLM becomes.

```bash
opsmate solve "how many cores on the server?" --max-iter 20
```

### Use various tools

The OpsMate can use various tools to solve the problem. You can see the list of available tools by running the `list-tools` command. To use these tools, you can pass the `--tools` option.

Here is an example of gathering top 10 news from hacker news and write it to a file:

```bash
opsmate solve \
  "find me top 10 news on the hacker news with bullet points and write to hn-top-10.md" \
  --tools HtmlToText,FileWrite
...

cat hn-top-10.md
# Top 10 Hacker News Stories

1. The FFT Strikes Back: An Efficient Alternative to Self-Attention
2. Telescope – an open-source web-based log viewer for logs stored in ClickHouse
3. DeepGEMM: clean and efficient FP8 GEMM kernels with fine-grained scaling
4. I Went to SQL Injection Court
5. Page is under construction: A love letter to the personal website
6. Hyperspace
7. Iterated Log Coding
8. Material Theme has been pulled from VS Code's marketplace
9. Part two of Grant Sanderson's video with Terry Tao on the cosmic distance ladder
10. Terence Tao – Machine-Assisted Proofs [video]
```

### Review and edit commands

Just like the [`run` command](./run.md), you can use the `--review` option to review and edit the commands before execution.

```bash
opsmate solve "how many cores on the server?" -r
```

### SEE ALSO

- [opsmate run](./run.md)
- [opsmate list-tools](./list-tools.md)
- [opsmate list-models](./list-models.md)
