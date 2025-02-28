`opsmate chat` allows you to use the OpsMate in an interactive chat interface.

## OPTIONS

```bash
Usage: opsmate chat [OPTIONS]

  Chat with the OpsMate.

Options:
  --model TEXT              OpenAI model to use. To list models available
                            please run the list-models command.  [default:
                            gpt-4o]
  --max-iter INTEGER        Max number of iterations the AI assistant can
                            reason about  [default: 10]
  -c, --context TEXT        Context to be added to the prompt. Run the list-
                            contexts command to see all the contexts
                            available.  [default: cli]
  --tools TEXT              Comma separated list of tools to use
  -r, --review              Review and edit commands before execution
  -s, --system-prompt TEXT  System prompt to use
  --help                    Show this message and exit.
```

## USAGE

### Basic

Herer is the most basic usage of the `opsmate chat` command:

```bash
OpsMate> Howdy! How can I help you?

Commands:

!clear - Clear the chat history
!exit - Exit the chat
!help - Show this message
```

### With a system prompt

You can use a system prompt with the `opsmate chat` command by using the `-s` or `--system-prompt` flag.

```bash
opsmate chat -s "you are a rabbit"
2025-02-26 18:10:12 [info     ] adding the plugin directory to the sys path plugin_dir=/home/jingkaihe/.opsmate/plugins
OpsMate> Howdy! How can I help you?

Commands:

!clear - Clear the chat history
!exit - Exit the chat
!help - Show this message

You> who are you

Answer

I am a rabbit, here to assist you with your queries and tasks.
You>
```
