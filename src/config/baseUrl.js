const DEFAULT_BASE_URL = 'http://localhost:3000';

function normalizeBaseUrl(url) {
  return url.endsWith('/') ? url.slice(0, -1) : url;
}

function getBaseUrl() {
  const fromEnv = process.env.BASE_URL;
  if (!fromEnv || !fromEnv.trim()) {
    return DEFAULT_BASE_URL;
  }

  return normalizeBaseUrl(fromEnv.trim());
}

module.exports = {
  DEFAULT_BASE_URL,
  getBaseUrl,
  normalizeBaseUrl,
};
