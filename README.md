# filenavi

## Synopsis

A simple web-based interface to manage and publish/embed files.

## Disclaimer

I have not yet actually tested whether this application is secure, so use it at
your own risk.

## Configuration

Writing a configuration file is as simple as this:

```ini
[filenavi]
icon_url=https://example.com/icon.svg # replace this URL with whatever you like
database_uri=sqlite:////var/lib/filenavi/filenavi.db # required
data_dir=/var/lib/filenavi/data # default: application instance directory
users_dir=users # relative to `data_dir`
```

Configuration files will be searched in this order:

1. `$XDG_CONFIG_HOME/config.ini`
2. `~/.config/filenavi/config.ini`
3. `/etc/filenavi/config.ini`

## Example installation

First, the service user has to be created, as follows:

```sh
useradd -r -s /bin/false filenavi
```

Next, clone the repository into `/opt`:

```sh
mkdir -p /opt/filenavi
git clone https://github.com/lukaswrz/filenavi /opt/filenavi
```

Now, the dependencies have to be installed. Make sure that they are either
installed globally or within a virtual environment. Here is how they would be
installed using the `requirements.txt` file in the repository:

```sh
pip install -r requirements.txt
```

Aside from Python dependencies, you need 2 database engines: Redis for session
data and an SQL database engine for user accounts. The SQL database is
user-defined inside of the database URI configuration option (`database_uri`),
which for simplicity in this case is defined as
`sqlite:////var/lib/filenavi/filenavi.db`.

Install Redis for session data (distribution-dependent):

```sh
pacman -S redis # or `apt install`, ...
```

Create the data directory:

```sh
mkdir -p /var/lib/filenavi/data
```

Set the correct permissions:

```sh
chmod -R 500 /opt/filenavi
chmod -R 700 /var/lib/filenavi
chmod -R 770 /var/lib/filenavi/data
chown -R filenavi:filenavi /opt/filenavi /var/lib/filenavi
```

Now is a good time to [create the configuration file](#configuration), as the
database initialization process requires the database URI to be defined.

Initialize the database:

```sh
runuser -u filenavi -- sh -c "FLASK_APP=filenavi FLASK_ENV=development flask init-db"
```

Create a systemd unit file, e.g. as `/etc/systemd/system/filenavi.service`:

```ini
[Unit]
Description=filenavi file service
After=network.target
AssertPathExists=/var/lib/filenavi

[Service]
User=filenavi
Type=simple
ExecStart=/usr/bin/uwsgi --plugin python --socket localhost:6670 --manage-script-name --module filenavi.wsgi:application
WorkingDirectory=/opt/filenavi
TimeoutStopSec=20
KillMode=mixed
Restart=on-failure
ReadWritePaths=/var/lib/filenavi
```

Now, nginx has to be configured to use uWSGI (`client_max_body_size` is
especially important here):

```nginx
server {
	# replace example.com with your domain name
	server_name example.com;

	location / {
		include uwsgi_params;
		uwsgi_pass localhost:6670;
	}

	sendfile on;
	# this is the request upload limit, adjust it according to your needs
	client_max_body_size 32G;

	# put your TLS configuration here instead:
	listen 80;
}
```

To finish the setup off, run the services:

```sh
systemctl start redis filenavi nginx
```

Now, you can login as the user "filenavi" with the password "filenavi". It is
of course highly recommended to change the username and password, as this user
has the owner rank, which means that it can basically do anything.

## Icons

You can set a custom header and tab icon via the `icon_url` configuration
option.

The remaining UI icons are from
[here](https://github.com/davidmerfield/Public-Icons), but have been altered
slightly.
