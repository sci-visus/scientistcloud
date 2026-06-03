# ScientistCloud — New Server Deploy Guide

Deploy **ScientistCloud 2.0** on a fresh OVH (or similar) Ubuntu server.

**Deploy user:** `<DEPLOY_USER>` (not `ubuntu`) — your Linux account for git, Docker, and deploy scripts  
**Code layout:** three separate GitHub repos under `~/ScientistCloud2.0/`  
**Production script:** `scientistcloud/SC_Docker/allServicesStart.sh`

Fill in for your server (keep these in your private notes, not in git if sensitive):

| Placeholder | Example |
|-------------|---------|
| `<DEPLOY_USER>` | Linux user on the server (e.g. `amy`) |
| `<SERVER_HOSTNAME>` | OVH reverse DNS or your domain |
| `<SSH_HOST_ALIAS>` | Short name in Mac `~/.ssh/config` |
| `<SSH_KEY_FILE>` | Private key used to SSH to the box |

---

## Quick reference

| Item | Value |
|------|--------|
| SSH (Mac) | `Host <SSH_HOST_ALIAS>` → `User <DEPLOY_USER>`, `HostName <SERVER_HOSTNAME>` |
| Code root | `~/ScientistCloud2.0` (e.g. `/home/<DEPLOY_USER>/ScientistCloud2.0`) |
| Env file | `SCLib_TryTest/env.scientistcloud` |
| Storage | `~/dockerStartDir/VisStoreDataTemp` |
| Branches | `SCLib_TryTest` → `main`; `scientistCloudLib` + `scientistcloud` → `workingPrivateRepo` |

---

## Phase 0 — Before you SSH (account / DNS)

- [ ] **DNS** — If using `scientistcloud.com`, point A record to the server IP (or use IP hostname until DNS is ready).
- [ ] **MongoDB Atlas** — Choose `DB_NAME` (new empty DB, or reuse e.g. `OVH51` if sharing data). Update **both** `DB_NAME` and the database name in `MONGO_URL`.
- [ ] **Auth0** — Add new server URL / domain to Auth0 app settings (callback, logout, web origins). Ask admin if needed.
- [ ] **Google OAuth** — Add redirect URIs for the new host if using Google login.
- [ ] **GitHub** — Server needs SSH access to private repos (see [Phase 2](#phase-2--github-ssh-and-clone-repos)).

**MongoDB note:** A new `DB_NAME` does **not** need pre-populated collections. Collections and documents are created on first use; SCLib creates indexes when services start. Users appear on first Auth0 login.

---

## Phase 1 — Server setup (as `ubuntu`, then switch to `<DEPLOY_USER>`)

### 1.1 Install Docker (official repo)

Ubuntu’s default repos do **not** include `docker-compose-plugin`. Use Docker’s apt repo:

```bash
sudo apt remove -y docker docker-engine docker.io containerd runc 2>/dev/null || true

sudo apt update
sudo apt install -y ca-certificates curl

sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

docker --version
docker compose version
```

Reboot if the MOTD says a restart is required: `sudo reboot`

### 1.2 Create deploy user `<DEPLOY_USER>`

```bash
sudo adduser <DEPLOY_USER>
sudo usermod -aG sudo,docker,www-data <DEPLOY_USER>
```

| Group | Why |
|-------|-----|
| `sudo` | Admin commands |
| `docker` | Run `docker compose` without sudo |
| `www-data` | Read/write dataset dirs group-owned for containers |

**Log out and SSH back in as `<DEPLOY_USER>`** so groups apply.

### 1.3 SSH login for `<DEPLOY_USER>`

On server (once, as `ubuntu`):

```bash
sudo mkdir -p /home/<DEPLOY_USER>/.ssh
sudo cp /home/ubuntu/.ssh/authorized_keys /home/<DEPLOY_USER>/.ssh/authorized_keys
sudo chown -R <DEPLOY_USER>:<DEPLOY_USER> /home/<DEPLOY_USER>/.ssh
sudo chmod 700 /home/<DEPLOY_USER>/.ssh
sudo chmod 600 /home/<DEPLOY_USER>/.ssh/authorized_keys
```

On **Mac** `~/.ssh/config`:

```
Host <SSH_HOST_ALIAS>
  HostName <SERVER_HOSTNAME>
  User <DEPLOY_USER>
  IdentityFile <SSH_KEY_FILE>
  IdentitiesOnly yes
```

Test: `ssh <SSH_HOST_ALIAS>` → `whoami` should print `<DEPLOY_USER>`.

### 1.4 GitHub SSH for `<DEPLOY_USER>`

Deploy keys require **repo Admin** on `sci-visus/*`. Easier approach: add the **server public key** to your GitHub account (**Settings → SSH and GPG keys**).

On server as `<DEPLOY_USER>`:

```bash
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519_github -N "" -C "<DEPLOY_USER>-deploy-github"
cat ~/.ssh/id_ed25519_github.pub
# Paste into GitHub → Settings → SSH and GPG keys

cat >> ~/.ssh/config <<'EOF'
Host github.com
  HostName github.com
  User git
  IdentityFile ~/.ssh/id_ed25519_github
  IdentitiesOnly yes
EOF
chmod 600 ~/.ssh/config

ssh -T git@github.com
# Expected: Hi <your-github-username>! You've successfully authenticated...
```

If org uses SSO: **Configure SSO → Authorize** on that key for `sci-visus`.

### 1.5 `visudo` — passwordless vendor `chown`

`SC_Web/vendor/` is in git; `allServicesStart.sh` runs `sudo chown` before `git pull`. Allow it without a password prompt:

```bash
sudo EDITOR=emacs visudo -f /etc/sudoers.d/<DEPLOY_USER>-vendor-chown
```

Add this line (replace every `<DEPLOY_USER>` with your actual username):

```
<DEPLOY_USER> ALL=(ALL) NOPASSWD: /usr/bin/chown -R <DEPLOY_USER>\:<DEPLOY_USER> /home/<DEPLOY_USER>/ScientistCloud2.0/scientistcloud/SC_Web/vendor
```

```bash
sudo chmod 440 /etc/sudoers.d/<DEPLOY_USER>-vendor-chown
sudo visudo -c
sudo -n chown -R <DEPLOY_USER>:<DEPLOY_USER> /home/<DEPLOY_USER>/ScientistCloud2.0/scientistcloud/SC_Web/vendor
echo $?   # should print 0
```

### 1.6 `docker-compose` shim

SCLib `start.sh` calls `docker-compose`; Docker CE installs `docker compose` (v2 plugin). Add a shim **as `<DEPLOY_USER>`**:

```bash
echo '#!/bin/sh
exec docker compose "$@"' | sudo tee /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
docker-compose version
```

### 1.7 Optional tools

```bash
sudo apt install -y emacs php-cli php-curl php-mbstring php-xml unzip
```

---

## Phase 2 — GitHub SSH and clone repos

There is **no** single `ScientistCloud2.0` GitHub repo. Create a parent directory and clone **three** repos into it.

| Directory | GitHub repo | Branch |
|-----------|-------------|--------|
| `SCLib_TryTest/` | `amygooch/SCLib_TryTest` | `main` |
| `scientistCloudLib/` | `sci-visus/scientistCloudLib` | `workingPrivateRepo` |
| `scientistcloud/` | `sci-visus/scientistcloud` | `workingPrivateRepo` |

```bash
whoami    # must be <DEPLOY_USER>
export SC20_HOME=$HOME/ScientistCloud2.0
mkdir -p "$SC20_HOME"
cd "$SC20_HOME"

# 1) Env / test config
git clone git@github.com:amygooch/SCLib_TryTest.git
cd SCLib_TryTest && git checkout main && cd ..

# 2) SCLib backend
git clone git@github.com:sci-visus/scientistCloudLib.git
cd scientistCloudLib
git fetch origin
git checkout -B workingPrivateRepo origin/workingPrivateRepo
cd ..

# 3) Portal + Docker + dashboards
git clone git@github.com:sci-visus/scientistcloud.git
cd scientistcloud
git fetch origin
git checkout -B workingPrivateRepo origin/workingPrivateRepo
cd ..

ls -la "$SC20_HOME"
# Expect: SCLib_TryTest  scientistCloudLib  scientistcloud
```

Copy env from Mac (recommended):

```bash
# On Mac (use your SSH alias or user@hostname):
scp /path/to/env.scientistcloud \
  <SSH_HOST_ALIAS>:~/ScientistCloud2.0/SCLib_TryTest/env.scientistcloud
```

Or create/edit on server: `emacs ~/ScientistCloud2.0/SCLib_TryTest/env.scientistcloud`

---

## Phase 3 — Storage (before first `docker compose up`)

```bash
mkdir -p ~/dockerStartDir/VisStoreDataTemp
git clone git@github.com:visus-llc/VisStoreVolumeStorageTemplate.git \
  ~/dockerStartDir/VisStoreDataTemp

# Permissions for container writes
export VISUS_SERVER=/home/<DEPLOY_USER>/dockerStartDir/VisStoreDataTemp
sudo chgrp -R www-data "$VISUS_SERVER"
sudo chmod -R g+w "$VISUS_SERVER"
sudo chown -R <DEPLOY_USER>:www-data "$VISUS_SERVER"
```

Expected top-level dirs under `VisStoreDataTemp`: `upload`, `converted`, `sync`, `auth`, `tmp`, `db`, etc.

---

## Phase 4 — Configure `env.scientistcloud`

Edit `~/ScientistCloud2.0/SCLib_TryTest/env.scientistcloud`.

**Update at minimum:**

- `DEPLOY_SERVER`, `DOMAIN_NAME`, `SC_SERVER_URL`, `SC_DOMAIN`
- `SC20_HOME=/home/<DEPLOY_USER>/ScientistCloud2.0`
- `VISUS_SERVER=/home/<DEPLOY_USER>/dockerStartDir/VisStoreDataTemp`
- `VISUS_DB`, `VISUS_DATASETS`, `VISUS_TEMP`, `SCLIB_*`
- `MONGO_URL`, `DB_NAME`, `DB_PASS` (must match in URL path and `DB_NAME`)
- Auth0 / Google IDs for this deployment

**Important:** Do **not** use angle brackets in values — they break `source`:

```bash
# BAD — bash syntax error:
D_GIT_TOKEN=<INSERT_TOKEN>

# OK:
D_GIT_TOKEN=
# or a real token:
D_GIT_TOKEN=ghp_xxxxxxxx
```

**`D_GIT_TOKEN`:** Optional for Phase 5. Host git uses SSH. Token is only needed if a **Docker build** clones a private repo (e.g. SCLib background-service). Try empty first; add a **read-only fine-grained PAT** only if builds fail.

Example path block (use your real username in place of `<DEPLOY_USER>`):

```bash
SC20_HOME=/home/<DEPLOY_USER>/ScientistCloud2.0
VISUS_SERVER=/home/<DEPLOY_USER>/dockerStartDir/VisStoreDataTemp
VISUS_DB=$VISUS_SERVER/db/
VISUS_DATASETS=$VISUS_SERVER/
VISUS_TEMP=$VISUS_SERVER/tmp/
SC_CERTBOT_CONF=${SC20_HOME}/scientistcloud/SC_Docker/certbot/conf
SC_CERTBOT_WWW=${SC20_HOME}/scientistcloud/SC_Docker/certbot/www
```

Sync env into Docker (also done by `allServicesStart.sh`):

```bash
cp ~/ScientistCloud2.0/SCLib_TryTest/env.scientistcloud \
   ~/ScientistCloud2.0/scientistCloudLib/Docker/.env
cp ~/ScientistCloud2.0/SCLib_TryTest/env.scientistcloud \
   ~/ScientistCloud2.0/scientistcloud/SC_Docker/.env
```

Optional — Composer on host (before first portal container):

```bash
cd ~/ScientistCloud2.0/scientistcloud/SC_Web
curl -sS https://getcomposer.org/installer | php
php composer.phar install --no-dev --optimize-autoloader
```

---

## Phase 5 — First Docker / ScientistCloud stack

**Run as `<DEPLOY_USER>`:**

```bash
cd ~/ScientistCloud2.0/scientistcloud/SC_Docker
./allServicesStart.sh swdx
```

| Mode | Meaning |
|------|---------|
| `s` | SCLib (auth, FastAPI, background service) |
| `w` | SC_Web portal |
| `d` | Dashboards |
| `x` | Nginx + Dozzle + dashboard nginx configs |

**Later updates:**

```bash
./allServicesStart.sh          # git pull only
./allServicesStart.sh s w      # pull + rebuild portal/SCLib
./allServicesStart.sh swdx     # full stack
```

---

## Phase 6 — SSL (new server)

From `scientistcloud/SC_Docker/certbot/README.md`:

1. DNS must point to this host before Let's Encrypt succeeds.
2. Certs live under `scientistcloud/SC_Docker/certbot/` (not VisusDataPortalPrivate paths).

2.1  Re-sync and create dirs:
cd ~/ScientistCloud2.0/scientistcloud/SC_Docker
mkdir -p certbot/conf certbot/www
cp ~/ScientistCloud2.0/SCLib_TryTest/env.scientistcloud ./.env


sudo chown -R amy:amy certbot/conf certbot/www
sudo find certbot/conf -type d -exec chmod 755 {} \;
sudo find certbot/conf -type f -exec chmod 644 {} \;
# Keep private key tighter if you prefer:
sudo chmod 600 certbot/conf/archive/scientistcloud.com/privkey*.pem 2>/dev/null || true

 2.2 Confirm DNS (from Mac):
dig @8.8.8.8 +short scientistcloud.com A

3. Port 80 must be free for standalone certbot (nothing listening on 80):

sudo ss -tlnp | grep ':80 '
If something is on 80, stop it before certbot.

4. Firewall:


sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

5. 
cd ~/ScientistCloud2.0/scientistcloud/SC_Docker
# Stop anything on 80/443 if needed
docker stop scientistcloud-nginx 2>/dev/null || true
docker run --rm \
  -p 80:80 \
  -v "$(pwd)/certbot/conf:/etc/letsencrypt" \
  -v "$(pwd)/certbot/www:/var/www/certbot" \
  certbot/certbot certonly \
  --standalone \
  -d scientistcloud.com \
  --email "${SSL_EMAIL:-amy@visoar.com}" \
  --agree-tos \
  --no-eff-email

 NOTE:  Do **not** use `migrate-ssl-certs.sh` unless copying from an old server.
 
 
 After certs exist:  

cd ~/ScientistCloud2.0/scientistcloud/SC_Docker
./allServicesStart.sh x
 
---

## Phase 7 — Verify

| Check | Command |
|-------|---------|
| Containers | `docker ps` — look for `scientistcloud-portal`, `scientistcloud-nginx`, `sclib_*`, `dashboard_*` |
| Portal | `https://<DOMAIN>/portal/` |
| Logs | `docker logs scientistcloud-portal` |
| Stop legacy | `docker stop visstore_nginx visstore_user visstore_bg_service` if still running |

---

## Troubleshooting

### `Permission denied (publickey)` to GitHub

- Custom key name `id_ed25519_github` requires `~/.ssh/config` with `IdentityFile` (see Phase 1.4).
- Test: `ssh -i ~/.ssh/id_ed25519_github -T git@github.com`
- Add **account** SSH key on GitHub, not deploy keys, unless you have repo Admin.

### `docker-compose: command not found`

Install shim (Phase 1.6) or use Docker CE + compose plugin from Phase 1.1.

### `[sudo] password for <DEPLOY_USER>` during `allServicesStart.sh`

Only the vendor `chown` should be passwordless (Phase 1.5). Verify:

```bash
sudo -l
sudo -n chown -R <DEPLOY_USER>:<DEPLOY_USER> ~/ScientistCloud2.0/scientistcloud/SC_Web/vendor
```

### `env.scientistcloud: syntax error near unexpected token`

Remove `<INSERT_TOKEN>` and similar placeholders — use empty value or real token without `<>`.

### `vendor/` permission errors after portal runs

Container Composer may set `vendor/` to `www-data`. Helper script:

```bash
cd ~/ScientistCloud2.0/scientistcloud/SC_Docker
./fix_vendor_permissions.sh
```

### Clone directories missing

Every failed `git clone` leaves an empty parent. Fix GitHub SSH first, then re-run Phase 2 commands from `cd ~/ScientistCloud2.0`.

---

## Related docs

| Doc | Purpose |
|-----|---------|
| `ScientistCloud2.0/DEPLOYMENT_STEPS.md` | **Updates only** after stack is deployed |
| `ScientistCloud2.0/scientistcloud/SC_Docker/NGINX.md` | SC-native nginx |
| `ScientistCloud2.0/scientistcloud/SC_Docker/certbot/README.md` | TLS |
| `VisusDataPortalPrivate/Docker/README_DEPLOYMENT.md` | Legacy Visus stack + storage patterns |

---

## Appendix — Legacy VisStore deploy

<details>
<summary>Original VisStore / visus-dataportal-private deploy (click to expand)</summary>

### Requirements

- Ask Amy/Aashish to add new server to Auth0.

### On local machine — Google Drive credentials

Run `getGoogleDriveCredentials.py` on your Mac (needs `client_secrets.json`, `settings.yaml`, `pip install pydrive`). Copy resulting `credentials.json` to the remote machine.

### On remote machine

```bash
cd <home dir where you want code>
mkdir VisStore
export MY_HOME=<that dir>/VisStore/

git clone git@github.com:sci-visus/visus-dataportal-private.git
export VISUS_CODE=$MY_HOME/visus-dataportal-private

git clone git@github.com:visus-llc/VisStoreVolumeStorageTemplate.git
export VISUS_SERVER=$MY_HOME/VisStoreVolumeStorageTemplate
```

Edit `$VISUS_CODE/config/env.deploy` with `DEPLOY_SERVER`, `MONGO_URL`, `DB_NAME`, branches, `D_GIT_TOKEN`, etc.

```bash
cd $VISUS_CODE/Docker
./docker_start_fresh.sh
# or ./docker_build_start.sh
```

If `docker-compose` missing: `sudo apt install docker-compose` (legacy) or use Docker CE from Phase 1.1.

### Known issues — data permissions

```bash
docker exec -it visstore_bg_service /bin/bash
chgrp -R www-data /mnt/visus*
chmod -R g+w /mnt/visus*
```

### SSL — legacy `Docker/setup_ssl.sh`

See `VisusDataPortalPrivate/Docker/setup_ssl.sh` and `Docker/README_DEPLOYMENT.md` for Let's Encrypt on the legacy stack. SC 2.0 uses `scientistcloud/SC_Docker/certbot/` instead.

### Auth0 / Google for new machine

Update callback, logout, and web origin URLs in Auth0 and Google Cloud Console to match the new server hostname.

</details>
