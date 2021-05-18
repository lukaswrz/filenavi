# sfstash

## Synopsis

sfstash is a simple web-based interface to manage and publish/embed files.

## Disclaimer

I have not yet actually tested whether this application is secure, so use it at
your own risk.

## Screenshot

![Screenshot](https://2gbcss.net/sfstashscr.png)

## Configuration

Writing a configuration file is as simple as this:

```ini
[sfstash]
icon_url=https://example.com/icon.svg # replace this URL with whatever you like
database_uri=sqlite:////var/lib/sfstash/sfstash.db # required
data_dir=/var/lib/sfstash # default: application instance directory
```

Configuration files will be searched in this order:

1. `$XDG_CONFIG_HOME/config.ini`
2. `~/.config/sfstash/config.ini`
3. `/etc/sfstash/config.ini`

## Example installation

First, the service user has to be created, as follows:

```sh
useradd -r -s /bin/false sfstash
```

Next, clone the repository into `/opt`:

```sh
mkdir -p -m 755 /opt/sfstash
git clone https://github.com/lukaswrz/sfstash /opt/sfstash
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
`sqlite:////var/lib/sfstash/sfstash.db`.

Install Redis for session data (distribution-dependent):

```sh
yay -S redis # or `sudo apt install`, ...
```

Create the data directory:

```sh
mkdir -p -m 755 /var/lib/sfstash
```

Set the correct permissions:

```sh
chown -R sfstash /opt/sfstash /var/lib/sfstash
```

Now is a good time to [create the configuration file](#configuration), as the
database initialization process requires the database URI to be defined.

Initialize the database:

```sh
runuser -u sfstash -- sh -c "FLASK_APP=sfstash FLASK_ENV=development flask init-db"
```

Create a systemd unit file, e.g. as `/etc/systemd/system/sfstash.service`:

```ini
[Unit]
Description=sfstash file service
After=network.target
AssertPathExists=/var/lib/sfstash

[Service]
User=sfstash
Type=simple
ExecStart=/usr/bin/uwsgi --plugin python --socket :6670 --manage-script-name --module sfstash.wsgi:application
WorkingDirectory=/opt/sfstash
TimeoutStopSec=20
KillMode=mixed
Restart=on-failure
ReadWritePaths=/var/lib/sfstash
```

Now, nginx has to be configured to use uWSGI:

```nginx
server {
	# replace example.com with your domain name
	server_name example.com;

	location / {
		include uwsgi_params;
		uwsgi_pass localhost:6670;
	}

	sendfile on;

	# put your TLS configuration here instead:
	listen 80;
}
```

To finish the setup off, run the services:

```sh
systemctl start redis sfstash nginx
```

Now, you can login as the user "sfstash" with the password "sfstash". It is
of course highly recommended to change the username and password, as this user
has the `owner` rank, which means that it can do basically anything.

## Icons

You can set a custom header and tab icon via the `icon_url` configuration
option.

The remaining UI icons are from
[here](https://github.com/davidmerfield/Public-Icons), but have been slightly
altered.
