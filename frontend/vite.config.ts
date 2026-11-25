import {fileURLToPath} from 'node:url';
import {defineConfig, loadEnv} from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({command, mode, isPreview}) => {
  const env = loadEnv(mode, fileURLToPath(new URL('../', import.meta.url)), 'MONROE_');
  const token = command === 'serve' && !isPreview && env.MONROE_LOCAL_AUTO_CONNECT === '1'
    ? env.MONROE_API_TOKEN?.trim() : undefined;
  return {
    plugins: [react(), {
      name: 'monroe-local-api-auth',
      configureServer(server) {
        if (!token) return;
        server.middlewares.use((req, res, next) => {
          if (!req.url?.startsWith('/api')) return next();
          const origin = `http://${req.headers.host}`;
          if (req.socket.remoteAddress !== '127.0.0.1'
            || !/^127\.0\.0\.1:\d+$/.test(req.headers.host ?? '')
            || (req.headers.origin && req.headers.origin !== origin)
            || (!['GET', 'HEAD'].includes(req.method ?? '') && req.headers.origin !== origin)
            || (req.headers['sec-fetch-site'] && req.headers['sec-fetch-site'] !== 'same-origin')) {
            res.writeHead(403).end('Local API access requires the Vite app on 127.0.0.1');
            return;
          }
          next();
        });
      },
    }],
    define: {__MONROE_LOCAL_CONNECT__: JSON.stringify(Boolean(token))},
    build: {
      rolldownOptions: {
        output: {
          codeSplitting: {
            groups: [{name: 'react', test: /[\\/]node_modules[\\/](react|react-dom|scheduler)[\\/]/}],
          },
        },
      },
    },
    server: {
      host: '127.0.0.1',
      headers: token ? {'X-Frame-Options': 'DENY'} : undefined,
      proxy: {'/api': {
        target: 'http://127.0.0.1:8000',
        rewrite: path => path.replace(/^\/api/, ''),
        configure(proxy) {
          if (token) proxy.on('proxyReq', proxyReq => proxyReq.setHeader('Authorization', `Bearer ${token}`));
        },
      }},
    },
  };
});
