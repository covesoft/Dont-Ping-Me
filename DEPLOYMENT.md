# Linux hosting

The supplied systemd template runs one copy as a dedicated `nuhuh` user, from
`/opt/nuhuh`, with the token in `/etc/nuhuh.env`. Change the template paths/user
if you use an existing service account. For local setup, permissions, and data
management, see [OPERATING.md](OPERATING.md).

On an Ubuntu host with Git, Python 3.11+, and the matching venv package available:

```sh
sudo useradd --system --home /opt/nuhuh --shell /usr/sbin/nologin nuhuh
sudo git clone https://github.com/covesoft/Dont-Ping-Me.git /opt/nuhuh
sudo chown -R nuhuh:nuhuh /opt/nuhuh
sudo -u nuhuh python3 -m venv /opt/nuhuh/.venv
sudo -u nuhuh /opt/nuhuh/.venv/bin/python -m pip install -r /opt/nuhuh/requirements.txt
sudoedit /etc/nuhuh.env
```

Review the selected release before installing. In `/etc/nuhuh.env`, put:

```text
NUHUH_DISCORD_TOKEN=your_private_token
NUHUH_SOURCE_URL=https://github.com/covesoft/Dont-Ping-Me
```

Before starting, make the source URL identify the actual version being hosted.
Modified forks must publish their changes and use their own public source URL;
prefer an immutable commit/release. See [source access and license](OPERATING.md#source-access-and-license).

Then install the service:

```sh
sudo chown root:nuhuh /etc/nuhuh.env
sudo chmod 640 /etc/nuhuh.env
sudo cp /opt/nuhuh/deploy/nuhuh.service /etc/systemd/system/nuhuh.service
sudo systemctl daemon-reload
sudo systemctl enable --now nuhuh.service
sudo systemctl status nuhuh.service --no-pager
sudo journalctl -u nuhuh.service -n 50 --no-pager
```

Keep only one running copy per token/database. The bot's default data path is
`/opt/nuhuh/.nuhuh/bot.sqlite3`. Preserve that directory across code updates.
The environment file takes precedence over dotenv's default non-overriding load.

## Updating

Stop the service, pull the reviewed revision into `/opt/nuhuh`, install its
requirements using the venv, and start again. Use the operator/service account
that owns the checkout rather than running the application as root.

```sh
sudo systemctl stop nuhuh.service
sudo -u nuhuh git -C /opt/nuhuh pull --ff-only
sudo -u nuhuh /opt/nuhuh/.venv/bin/python -m pip install -r /opt/nuhuh/requirements.txt
sudo systemctl start nuhuh.service
```

If an alpha schema is incompatible, startup identifies the database and asks
for a reset. With the service stopped, remove that database and matching
sidecars, then restart. No automatic migration is carried in this release.

For a simple consistent backup, stop the service, copy the database, then start
again. Keep backups private and apply record deletions to retained copies.

After deployment, verify a mention, the cooldown, a clean stop/start with the
same count history, and service startup after reboot. Track these checks for
your installation using the [release checklist](RELEASE_CHECKLIST.md).
