`opsmate list-tools` lists all the tools available.

## OPTIONS

```
Usage: opsmate list-tools [OPTIONS]

  List all the tools available.

Options:
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
  --embeddings-db-path TEXT       The path to the lance db. When s3:// is used
                                  for AWS S3, az:// is used for Azure Blob
                                  Storage, and gs:// is used for Google Cloud
                                  Storage (env: OPSMATE_EMBEDDINGS_DB_PATH)
                                  [default: /root/.opsmate/embeddings]
  --contexts-dir TEXT             Set contexts_dir (env: OPSMATE_CONTEXTS_DIR)
                                  [default: /root/.opsmate/contexts]
  --plugins-dir TEXT              Set plugins_dir (env: OPSMATE_PLUGINS_DIR)
                                  [default: /root/.opsmate/plugins]
  --db-url TEXT                   Set db_url (env: OPSMATE_DB_URL)  [default:
                                  sqlite:////root/.opsmate/opsmate.db]
  --help                          Show this message and exit.
```

## USAGE

The command below will list all the tools available to Opsmate. Notes the plugins can be installed in the `~/.opsmate/plugins` directory. The example you see below only lists all the built-in tools.

```bash
opsmate list-tools
2025-02-26 12:03:25 [info     ] adding the plugin directory to the sys path plugin_dir=/home/your-username/.opsmate/plugins
                                                   Tools
┏━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Tool                ┃ Description                                                                        ┃
┡━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ ACITool             │                                                                                    │
│                     │     # ACITool                                                                      │
│                     │                                                                                    │
│                     │     File system utility with the following commands:                               │
│                     │                                                                                    │
│                     │     search <file|dir> <content>           # Search in file/directory               │
│                     │     view <file|dir>          # View file (optional 0-indexed line range) or        │
│                     │ directory                                                                          │
│                     │     create <file> <content>          # Create new file                             │
│                     │     update <file> <old> <new>         # Replace content (old must be unique), with │
│                     │ optional 0-indexed line range                                                      │
│                     │     append <file> <line> <content>   # Insert at line number                       │
│                     │     undo <file>                      # Undo last file change                       │
│                     │                                                                                    │
│                     │     Notes:                                                                         │
│                     │     - Line numbers are 0-indexed                                                   │
│                     │     - Directory view: 2-depth, ignores dotfiles                                    │
│                     │     - Empty new content in update deletes old content                              │
│                     │                                                                                    │
├─────────────────────┼────────────────────────────────────────────────────────────────────────────────────┤
│ FileAppend          │ FileAppend tool allows you to append to a file                                     │
├─────────────────────┼────────────────────────────────────────────────────────────────────────────────────┤
│ FileDelete          │ FileDelete tool allows you to delete a file                                        │
├─────────────────────┼────────────────────────────────────────────────────────────────────────────────────┤
│ FileRead            │ FileRead tool allows you to read a file                                            │
├─────────────────────┼────────────────────────────────────────────────────────────────────────────────────┤
│ FileWrite           │ FileWrite tool allows you to write to a file                                       │
├─────────────────────┼────────────────────────────────────────────────────────────────────────────────────┤
│ FilesFind           │ FilesFind tool allows you to find files in a directory                             │
├─────────────────────┼────────────────────────────────────────────────────────────────────────────────────┤
│ FilesList           │ FilesList tool allows you to list files in a directory recursively                 │
├─────────────────────┼────────────────────────────────────────────────────────────────────────────────────┤
│ GithubCloneAndCD    │                                                                                    │
│                     │     Clone a github repository and cd into the directory                            │
│                     │                                                                                    │
├─────────────────────┼────────────────────────────────────────────────────────────────────────────────────┤
│ GithubRaisePR       │                                                                                    │
│                     │     Raise a PR for a given github repository                                       │
│                     │                                                                                    │
├─────────────────────┼────────────────────────────────────────────────────────────────────────────────────┤
│ HtmlToText          │ HtmlToText tool allows you to convert an HTTP response to text                     │
├─────────────────────┼────────────────────────────────────────────────────────────────────────────────────┤
│ HttpCall            │                                                                                    │
│                     │     HttpCall tool allows you to call a URL                                         │
│                     │     Supports POST, PUT, DELETE, PATCH                                              │
│                     │                                                                                    │
├─────────────────────┼────────────────────────────────────────────────────────────────────────────────────┤
│ HttpGet             │ HttpGet tool allows you to get the content of a URL                                │
├─────────────────────┼────────────────────────────────────────────────────────────────────────────────────┤
│ KnowledgeRetrieval  │                                                                                    │
│                     │     Knowledge retrieval tool allows you to search for relevant knowledge from the  │
│                     │ knowledge base.                                                                    │
│                     │                                                                                    │
├─────────────────────┼────────────────────────────────────────────────────────────────────────────────────┤
│ ShellCommand        │                                                                                    │
│                     │     ShellCommand tool allows you to run shell commands and get the output.         │
│                     │                                                                                    │
├─────────────────────┼────────────────────────────────────────────────────────────────────────────────────┤
│ SysEnv              │ SysEnv tool allows you to get the environment variables                            │
├─────────────────────┼────────────────────────────────────────────────────────────────────────────────────┤
│ SysStats            │ SysStats tool allows you to get the stats of a file                                │
├─────────────────────┼────────────────────────────────────────────────────────────────────────────────────┤
│ current_time        │                                                                                    │
│                     │     Get the current time in %Y-%m-%dT%H:%M:%SZ format                              │
│                     │                                                                                    │
├─────────────────────┼────────────────────────────────────────────────────────────────────────────────────┤
│ datetime_extraction │                                                                                    │
│                     │     You are tasked to extract the datetime range from the text                     │
│                     │                                                                                    │
└─────────────────────┴────────────────────────────────────────────────────────────────────────────────────┘
```
