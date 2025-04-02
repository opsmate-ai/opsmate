`opsmate install` installs Opsmate plugins as python packages.

Currently there are two types python package based plugins that are supported:

- `opsmate-provider-*`: These are the language model providers.
- `opsmate-runtime-*`: These are the runtime environments that can be used to run the Opsmate.


## OPTIONS

```
Usage: opsmate install [OPTIONS] [PACKAGES]...

  Install the opsmate plugins.

Options:
  -U, --upgrade        Upgrade the given packages to the latest version
  --force-reinstall    Reinstall all packages even if they are already up-to-
                       date
  -e, --editable TEXT  Install a project in editable mode (i.e. setuptools
                       "develop mode") from a local project path or a VCS url
  --no-cache-dir       Disable the cache
  --help               Show this message and exit.
```

## SEE ALSO

- [Add New LLM Providers](../integrations/add-new-llm-providers.md)
- [Integrate with New Runtime](../integrations/integrate-with-new-runtime.md)
- [Uninstall](./uninstall.md)
