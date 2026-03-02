const assert = require('assert');
const { DEFAULT_BASE_URL, getBaseUrl, normalizeBaseUrl } = require('../src/config/baseUrl');
const { buildApiUrl } = require('../src/api/client');

function withEnv(key, value, fn) {
  const current = process.env[key];

  if (value === undefined) {
    delete process.env[key];
  } else {
    process.env[key] = value;
  }

  try {
    fn();
  } finally {
    if (current === undefined) {
      delete process.env[key];
    } else {
      process.env[key] = current;
    }
  }
}

withEnv('BASE_URL', undefined, () => {
  assert.strictEqual(getBaseUrl(), DEFAULT_BASE_URL);
});

withEnv('BASE_URL', 'https://api.example.com/', () => {
  assert.strictEqual(getBaseUrl(), 'https://api.example.com');
  assert.strictEqual(buildApiUrl('transactions'), 'https://api.example.com/transactions');
});

assert.strictEqual(normalizeBaseUrl('https://example.com/'), 'https://example.com');
assert.strictEqual(normalizeBaseUrl('https://example.com'), 'https://example.com');

console.log('All base URL checks passed.');
