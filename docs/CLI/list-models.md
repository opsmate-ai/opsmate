`opsmate list-models` lists all the models available.

Currently on Opsmate we cherry-pick the models that are suitable for performing SRE/DevOps oriented tasks that being said in the future we will look into supporting extra models through the plugin system.

## OPTIONS

```
Usage: opsmate list-models [OPTIONS]

  List all the models available.

Options:
  --help  Show this message and exit.
```

## USAGE

```bash
opsmate list-models

                  Models
┏━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Provider  ┃ Model                      ┃
┡━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ openai    │ gpt-4o                     │
├───────────┼────────────────────────────┤
│ openai    │ gpt-4o-mini                │
├───────────┼────────────────────────────┤
│ openai    │ o1-preview                 │
├───────────┼────────────────────────────┤
│ anthropic │ claude-3-5-sonnet-20241022 │
├───────────┼────────────────────────────┤
│ anthropic │ claude-3-7-sonnet-20250219 │
├───────────┼────────────────────────────┤
│ xai       │ grok-2-1212                │
└───────────┴────────────────────────────┘
```

## SEE ALSO

- [Add new LLM providers](../integrations/add-new-llm-providers.md)
