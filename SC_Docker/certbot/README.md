# ScientistCloud TLS (Let's Encrypt)

Certificates for `scientistcloud-nginx` live here — **not** under VisusDataPortalPrivate.

```
SC_Docker/certbot/
├── conf/          # mounted as /etc/letsencrypt (live/, archive/, renewal/)
└── www/           # ACME webroot (/var/www/certbot)
```

Set in `SCLib_TryTest/env.scientistcloud` (per host):

```bash
SC20_HOME=/home/amy/ScientistCloud2.0
SC_CERTBOT_CONF=${SC20_HOME}/scientistcloud/SC_Docker/certbot/conf
SC_CERTBOT_WWW=${SC20_HOME}/scientistcloud/SC_Docker/certbot/www
```

## One-time migration from legacy Visus deploy

On the current server only (paths will differ elsewhere):

```bash
cd scientistcloud/SC_Docker
./scripts/migrate-ssl-certs.sh /home/amy/VisStoreClone/visus-dataportal-private/Docker/certbot
```

Then restart nginx: `./allServicesStart.sh x`

## New server

1. Copy this `certbot/` tree (or re-issue with certbot using the same `DOMAIN_NAME`).
2. Set `SC20_HOME`, `SC_CERTBOT_*` in `env.scientistcloud`.
3. Do not install `visus-dataportal-private` for SC 2.0 edge.

`conf/` and `www/` are gitignored (secrets on disk only).
