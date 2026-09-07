// Jest-only Babel config (Vite itself never reads this — it uses esbuild).
// `transform-vite-meta-env` rewrites `import.meta.env.X` to `process.env.X`
// so modules like lib/api/client.ts, written for Vite, also run under
// Jest's CommonJS transform without any source changes. TSX needs its own
// override (isTSX + allExtensions) — without it, generic syntax like
// `useRef<T>()` inside a .tsx file is ambiguous with JSX and fails to parse.
module.exports = {
  presets: [['@babel/preset-env', { targets: { node: 'current' } }], ['@babel/preset-react', { runtime: 'automatic' }]],
  plugins: ['babel-plugin-transform-vite-meta-env'],
  overrides: [
    {
      test: /\.tsx$/,
      presets: [['@babel/preset-typescript', { isTSX: true, allExtensions: true }]],
    },
    {
      test: /\.ts$/,
      presets: ['@babel/preset-typescript'],
    },
  ],
};
