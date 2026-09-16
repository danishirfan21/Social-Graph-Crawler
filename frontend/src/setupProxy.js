const { createProxyMiddleware } = require('http-proxy-middleware');

/**
 * Keep browser requests same-origin in local and Codespaces development.
 * This explicit middleware also works when Codespaces forwards port 3000 to
 * a different local port (for example, localhost:3001).
 */
module.exports = function configureProxy(app) {
  app.use(
    ['/api', '/docs', '/openapi.json', '/ready', '/health'],
    createProxyMiddleware({ target: 'http://localhost:8000', changeOrigin: true })
  );
};
