MySQLTool is a tool that allows you to interact with MySQL databases.

## Installation

The MySQLTool is not pre-installed with Opsmate. You need to install it explicitly:

```bash
opsmate install opsmate-tools-mysql
```

Once installed, the tool will be autodiscovered by Opsmate on startup. To verify this you can run the following commands:

```bash
opsmate list-tools | grep -i mysql
│ MySQLTool           │ MySQL tool
```

The command line options will be added to the `opsmate [run|solve|chat|serve]` commands:

```bash
# to verify the mysql runtime is autodiscovered
opsmate chat --help | grep -i mysql
  --runtime-mysql-timeout INTEGER
                                  The timeout of the MySQL server (env:
                                  RUNTIME_MYSQL_TIMEOUT)  [default: 120]
  --runtime-mysql-charset TEXT    The charset of the MySQL server (env:
                                  RUNTIME_MYSQL_CHARSET)  [default: utf8mb4]
  --runtime-mysql-database TEXT   The database of the MySQL server (env:
                                  RUNTIME_MYSQL_DATABASE)
  --runtime-mysql-password TEXT   The password of the MySQL server (env:
                                  RUNTIME_MYSQL_PASSWORD)  [default: ""]
  --runtime-mysql-user TEXT       The user of the MySQL server (env:
                                  RUNTIME_MYSQL_USER)  [default: root]
  --runtime-mysql-port INTEGER    The port of the MySQL server (env:
                                  RUNTIME_MYSQL_PORT)  [default: 3306]
  --runtime-mysql-host TEXT       The host of the MySQL server (env:
                                  RUNTIME_MYSQL_HOST)  [default: localhost]
```

## Show Cases

Here is an example of "chatting" with the `x-for-pet` database using Opsmate:

<script
  src="https://asciinema.org/a/gnZBCx6hO9fq0AM4Pvzv5oFCg.js"
  id="asciicast-gnZBCx6hO9fq0AM4Pvzv5oFCg"
  async="true"
  data-theme="solarized-dark"
  data-speed="2"
  data-loop=true
  data-autoplay=true
  data-rows="30"
></script>

Here is another example of Claude Sonnet 3.7 conducting database schema analysis (the text size is a bit small, please feel free to zoom in):

<script
  src="https://asciinema.org/a/3FNuT7JdySxnAM29GUdXuqw6L.js"
  id="asciicast-3FNuT7JdySxnAM29GUdXuqw6L"
  async="true"
  data-theme="solarized-dark"
  data-speed="2"
  data-loop=true
  data-autoplay=true
  data-rows="50"
></script>


## Uninstallation

```bash
opsmate uninstall -y opsmate-tools-mysql
```
