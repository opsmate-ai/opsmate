`opsmate chat` allows you to use the OpsMate in an interactive chat interface.

## OPTIONS

```bash
Usage: opsmate chat [OPTIONS]

  Chat with the OpsMate.

Options:
  -i, --max-iter INTEGER          Max number of iterations the AI assistant
                                  can reason about  [default: 10]
  -c, --context TEXT              Context to be added to the prompt. Run the
                                  list-contexts command to see all the
                                  contexts available.  [default: cli]
  --tool-calls-per-action INTEGER
                                  Number of tool calls per action  [default:
                                  1]
  -m, --model TEXT                Large language model to use. To list models
                                  available please run the list-models
                                  command.  [default: gpt-4o]
  --tools TEXT                    Comma separated list of tools to use
  -r, --review                    Review and edit commands before execution
  -s, --system-prompt TEXT        System prompt to use
  -l, --max-output-length INTEGER
                                  Max length of the output, if the output is
                                  truncated, the tmp file will be printed in
                                  the output  [default: 10000]
  --loglevel TEXT                 Set loglevel (env: OPSMATE_LOGLEVEL)
                                  [default: INFO]
  --categorise BOOLEAN            Whether to categorise the embeddings (env:
                                  OPSMATE_CATEGORISE)  [default: True]
  --reranker-name TEXT            The name of the reranker model (env:
                                  OPSMATE_RERANKER_NAME)  [default: ""]
  --embedding-model-name TEXT     The name of the embedding model (env:
                                  OPSMATE_EMBEDDING_MODEL_NAME)  [default:
                                  text-embedding-ada-002]
  --embedding-registry-name TEXT  The name of the embedding registry (env:
                                  OPSMATE_EMBEDDING_REGISTRY_NAME)  [default:
                                  openai]
  --embeddings-db-path TEXT       The path to the lance db (env:
                                  OPSMATE_EMBEDDINGS_DB_PATH)  [default:
                                  /root/.opsmate/embeddings]
  --contexts-dir TEXT             Set contexts_dir (env: OPSMATE_CONTEXTS_DIR)
                                  [default: /root/.opsmate/contexts]
  --plugins-dir TEXT              Set plugins_dir (env: OPSMATE_PLUGINS_DIR)
                                  [default: /root/.opsmate/plugins]
  --db-url TEXT                   Set db_url (env: OPSMATE_DB_URL)  [default:
                                  sqlite:////root/.opsmate/opsmate.db]
  --help                          Show this message and exit.
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
