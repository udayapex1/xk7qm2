import tsParser from '@typescript-eslint/parser';
import tsPlugin from '@typescript-eslint/eslint-plugin';
import hooks from 'eslint-plugin-react-hooks';

export default [{ ignores: ['dist', 'node_modules'] }, { files: ['**/*.{ts,tsx}'], languageOptions: { parser: tsParser, parserOptions: { ecmaVersion: 'latest', sourceType: 'module', ecmaFeatures: { jsx: true } } }, plugins: { '@typescript-eslint': tsPlugin, 'react-hooks': hooks }, rules: { ...tsPlugin.configs.recommended.rules, ...hooks.configs.recommended.rules } }];
