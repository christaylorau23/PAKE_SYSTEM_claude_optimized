import js from '@eslint/js';
import globals from 'globals';
import tseslint from 'typescript-eslint';
import pluginReact from 'eslint-plugin-react';
import prettierConfig from 'eslint-config-prettier';
import { defineConfig } from 'eslint/config';

export default defineConfig([
  {
    files: ['**/*.{js,mjs,cjs,ts,mts,cts,jsx,tsx}'],
    plugins: { js },
    extends: ['js/recommended'],
    languageOptions: { globals: { ...globals.browser, ...globals.node } },
  },
  tseslint.configs.recommended,
  pluginReact.configs.flat.recommended,
  {
    files: [
      '**/*.test.{js,ts,jsx,tsx}',
      '**/test/**/*.{js,ts,jsx,tsx}',
      '**/tests/**/*.{js,ts,jsx,tsx}',
      '**/jest.setup.js',
    ],
    languageOptions: {
      globals: {
        ...globals.jest,
        ...globals.node,
        ...globals.browser,
      },
    },
  },
  {
    settings: {
      react: {
        version: 'detect',
      },
    },
  },
  {
    ignores: [
      'node_modules/**',
      'venv/**',
      '.venv/**',
      '__pycache__/**',
      '*.pyc',
      '.pytest_cache/**',
      '.coverage',
      'dist/**',
      'build/**',
      '.next/**',
      'out/**',
      'frontend/.next/**',
      'frontend/build/**',
      'frontend/dist/**',
      'frontend/out/**',
      '*.min.js',
      '*.bundle.js',
      '*.chunk.js',
      'test_env/**',
    ],
  },
  // Prettier config must be last to override conflicting ESLint rules
  prettierConfig,
]);
