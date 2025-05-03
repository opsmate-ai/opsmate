## Default LLM Model

The default LLM model can be specified via `--model` or `-m` flag through the command line on the program startup.

It can also be specified as `OPSMATE_MODEL` environment variable, e.g.

```bash
export OPSMATE_MODEL="gpt-4.1"
```

Alternatively, you can also save the model configuration in the `~/.opsmate/config.yaml` file.

```yaml
---
# ...
OPSMATE_MODEL: claude-3-7-sonnet-20250219
# ...
```

## LLM Configuration

There are more nuanced configurations for the LLM, such as temperatures, top_p, thinking budget, etc.

Here is the out of box configurations:

```yaml
OPSMATE_MODELS_CONFIG:
  claude-3-7-sonnet-20250219:
    thinking:
      budget_tokens: 1024
      type: enabled
  grok-3-mini-beta:
    reasoning_effort: medium
    tool_call_model: grok-3-beta
  grok-3-mini-fast-beta:
    reasoning_effort: medium
    tool_call_model: grok-3-beta
  o1:
    reasoning_effort: medium
    tool_call_model: gpt-4.1
  o3:
    reasoning_effort: medium
    tool_call_model: gpt-4.1
  o3-mini:
    reasoning_effort: medium
    tool_call_model: gpt-4.1
  o4-mini:
    reasoning_effort: medium
    tool_call_model: gpt-4.1
```

Note that in the configuration above, we use tool call models as the supplemental model for the reasoning models, this is because while reasoning models are capable of reasoning, in many use cases they are not very effective at tool calling.

To override the default configurations, you can copy and paste the above configurations to your `~/.opsmate/config.yaml` file, and override the specific configurations you want to change.

## Claude 3.7 Sonnet for Thinking

The `claude-3-7-sonnet-20250219` model is a powerful reasoning model with `thinking` enabled. To enable you can add the following configuration to your `~/.opsmate/config.yaml` file:

```yaml
OPSMATE_MODELS_CONFIG:
  claude-3-7-sonnet-20250219:
    thinking:
      budget_tokens: 1024
      type: enabled
  # ...
```
