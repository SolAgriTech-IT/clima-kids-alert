# TLS termination with Nginx on Ubuntu (VPS)

This guide assumes:

- DNS points your domain to the VPS public IP.
- Docker Compose runs the stack from this repository.
- You will obtain **Let’s Encrypt** certificates using **Certbot**.

## 1) Open ports

Allow inbound **80/tcp** and **443/tcp** (and restrict SSH appropriately).

## 2) Issue certificates (Certbot standalone or webroot)

### Option A — Certbot standalone (simplest for first issuance)

Stop anything bound to port **80** temporarily, then:

```bash
sudo certbot certonly --standalone -d your.domain.example --agree-tos -m you@example.com
```

### Option B — HTTP-01 via Nginx webroot (recommended once Nginx is up)

Ensure Nginx serves `/.well-known/acme-challenge/` from `/var/www/certbot` (the default `nginx/conf.d/10-http.conf` already includes this location).

Then:

```bash
sudo certbot certonly --webroot -w /var/www/certbot -d your.domain.example
```

Certificates will typically be written to:

- `/etc/letsencrypt/live/your.domain.example/fullchain.pem`
- `/etc/letsencrypt/live/your.domain.example/privkey.pem`

## 3) Enable HTTPS in Nginx

1. Copy the example TLS server block:

```bash
cp nginx/conf.d/50-https.conf.example nginx/conf.d/50-https.conf
```

2. Edit `nginx/conf.d/50-https.conf`:

- Replace `server_name` with your domain.
- Replace `ssl_certificate` / `ssl_certificate_key` paths if your layout differs.

3. Start Compose with the TLS overlay (mounts host cert paths read-only):

```bash
docker compose -f docker-compose.yml -f docker-compose.ssl.yml up -d --build
```

## 4) Redirect HTTP → HTTPS (recommended)

Replace `nginx/conf.d/10-http.conf` with a server that:

- serves `/.well-known/acme-challenge/` from `/var/www/certbot`
- returns **301** for all other paths to `https://$host$request_uri`

Use `nginx/conf.d/10-http.https-redirect.example` as a starting point (copy to `10-http.conf`).

## 5) Application configuration updates

- Set `CORS_ORIGINS` to your HTTPS origin(s), e.g. `https://your.domain.example`.
- Terminate TLS at Nginx; you can keep backend containers on HTTP inside the Docker network.

## 6) Hardening checklist

- Firewall: allow **80/443** only as needed.
- Renewals: install Certbot renewal hooks (`certbot renew`) and reload Nginx after renewal.
- Optional: OCSP stapling and Mozilla “intermediate” TLS profile (see `50-https.conf.example` baseline).
