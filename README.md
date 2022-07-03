# filenavi

## Synopsis

A simple web-based interface to manage and publish/embed files.

## Configuration

Writing a configuration file is as simple as this:

```ini
[filenavi]
database_uri=sqlite:////var/lib/filenavi/filenavi.db
data_dir=/var/lib/filenavi/data
users_dir=users
```

Configuration files will be searched in this order:

1. `/etc/filenavi/config.ini`
2. `config.ini`

## Installation

First, the service user has to be created, as follows:

```bash
useradd --system --shell /usr/bin/nologin filenavi
```

Next, the repository needs to be cloned. I will choose to clone it into
`/usr/local/share/webapps`:

```bash
mkdir --parents /usr/local/share/webapps/filenavi
chown filenavi:filenavi /usr/local/share/webapps/filenavi
runuser -u filenavi -- git clone https://github.com/lukaswrz/filenavi.git /usr/local/share/webapps/filenavi
```

Now, the dependencies have to be installed. Make sure that they are either
installed globally or within a virtual environment. A `requirements.txt` file
is provided in the Git repository.

For example:

```bash
pushd /usr/local/share/webapps/filenavi
runuser -u filenavi -- python -m venv venv
runuser -u filenavi -- venv/bin/pip install -r requirements.txt
popd
```

Aside from Python dependencies, you need 2 database engines: Redis for session
data and an SQL database engine for user accounts. The SQL database is
user-defined inside of the database URI [configuration](#configuration) option
(`database_uri`), which for simplicity in this case is defined as
`sqlite:////var/lib/filenavi/filenavi.db`.

Install Redis for session data (distribution-dependent):

```bash
pacman -S redis
```

Create the data directory:

```bash
mkdir --parents /var/lib/filenavi/data
```

Set the correct permissions:

```bash
chmod 700 /var/lib/filenavi /var/lib/filenavi/data
chown filenavi:filenavi /var/lib/filenavi
```

Now is a good time to [create the configuration file](#configuration), as the
database initialization process requires the database URI to be defined.

Initialize the database:

```bash
pushd /usr/local/share/webapps/filenavi
runuser -u filenavi -- env FLASK_APP=filenavi FLASK_ENV=development venv/bin/flask init-db
popd
```

Install uWSGI for the reverse proxy (distribution-dependent):

```bash
pacman -S uwsgi
```

Create a uWSGI configuration file, e.g. as `/etc/uwsgi/filenavi.ini`:

```ini
[uwsgi]
http-socket = :6670

uid = filenavi
gid = filenavi

disable-logging = false

# Adjust this to the desired number of workers.
workers = 4

chmod-socket = 666

single-interpreter = true
master = true
plugin = python
lazy-apps = true
enable-threads = true

module = filenavi.wsgi

virtualenv = /usr/local/share/webapps/filenavi/venv
chdir = /usr/local/share/webapps/filenavi
```

For uWSGI to work, there needs to be a systemd service file to launch it as a
service. This file is shipped with the `uwsgi` package on Arch Linux, but on
systems that do not ship this file, you're going to have to write one on your
own.

Now, nginx has to be configured to use uWSGI (`client_max_body_size` is
especially important here):

```nginx
server {
    # Replace this with your domain name.
    server_name example.com;

    location / {
        proxy_pass http://localhost:6670;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    sendfile on;

    # This is the request upload limit, adjust it according to your needs.
    client_max_body_size 32G;

    # Put your TLS configuration here instead.
    listen 80;
}
```

To finish the setup off, run the services:

```bash
systemctl start redis.service uwsgi@filenavi.service nginx.service
```

Now, you can login as the user "filenavi" with the password "filenavi". It is
of course highly recommended to change the username and password, as this user
has the owner rank, which means that it can basically do anything.
