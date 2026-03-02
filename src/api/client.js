const { getBaseUrl } = require('../config/baseUrl');

function buildApiUrl(path = '') {
  const baseUrl = getBaseUrl();
  const cleanPath = path.startsWith('/') ? path : `/${path}`;
  return `${baseUrl}${cleanPath}`;
}

module.exports = {
  buildApiUrl,
};
