`opsmate list-tools` lists all the tools available.

## USAGE

The command below will list all the tools available to OpsMate. Notes the plugins can be installed in the `~/.opsmate/plugins` directory. The example you see below only lists all the built-in tools.

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
