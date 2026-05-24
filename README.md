# fejoh.com

Catalog site for games by Felix.

- Live at https://fejoh.com
- Single static page (no build step). Edit `index.html` to change content.

## Hosting

Served on a tiny `nginx:alpine` container behind Caddy on the family VPS.

To edit the live site by hand:

    ssh cjoh@195.35.14.126
    cd /home/cjoh/fejoh-site
    # edit index.html — nginx mounts it read-from-host, no rebuild needed
