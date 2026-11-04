# Linux hosting

The supplied systemd template runs one copy as a dedicated `nuhuh` user, from
`/opt/nuhuh`, with the token in `/etc/nuhuh.env`. Change the template paths/user
if you use an existing service account. This file prepares deployment; it does
not mean a hosted service has been installed or verified.

On an Ubuntu host with Git, Python 3.11+, and the matching venv package available:

```sh
sudo useradd --system --home /opt/nuhuh --shell /usr/sbin/nologin nuhuh
sudo git clone https://github.com/covesoft/Dont-Ping-Me.git /opt/nuhuh
sudo chown -R nuhuh:nuhuh /opt/nuhuh
sudo -u nuhuh python3 -m venv /opt/nuhuh/.venv
sudo -u nuhuh /opt/nuhuh/.venv/bin/python -m pip install -r /opt/nuhuh/requirements.txt
sudoedit /etc/nuhuh.env
```

Use the revision containing v0.3.0; the new files must be pushed to your
repository before a fresh clone can receive them. In `/etc/nuhuh.env`, put:

```text
NUHUH_DISCORD_TOKEN=your_private_token
```

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
same count history, and service startup after reboot. The service template itself
has not been run against the user's VPS from this workspace.
