# fejoh.com

Catalog site for games by Felix. Live at https://fejoh.com.

## What's in here

- `index.html` — the whole site (single static page, no build step)
- `docker-compose.yml` — runs nginx (serving the site) + a deploy listener
- `Dockerfile.deploy` + `deploy_listener.py` — GitHub webhook receiver

## Editing

1. Edit `index.html`
2. Commit and push to `main`
3. GitHub fires a webhook at `https://fejoh.com/__deploy`
4. The listener verifies the signature and runs `git pull` on the server
5. nginx serves the new file instantly (no rebuild needed)

## Server

Runs on `cjoh@195.35.14.126` at `/home/cjoh/fejoh-site`, behind Caddy on
the shared `twenty_default` Docker network.
