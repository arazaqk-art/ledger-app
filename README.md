# Ledger App

This repository now includes a small **base URL configuration layer** so the app can run against different environments (local, staging, production) without code changes.

## Base URL setup

Set `BASE_URL` before starting your app:

```bash
BASE_URL=https://api.example.com node src/example.js
```

If `BASE_URL` is not set, it falls back to `http://localhost:3000`.

## Files

- `src/config/baseUrl.js` – resolves the app's base URL.
- `src/api/client.js` – safely builds endpoint URLs from the base URL.
- `src/example.js` – small usage example.
- `tests/baseUrl.test.js` – quick validation checks.

## Run checks

```bash
node tests/baseUrl.test.js
```
