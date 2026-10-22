# Next.js Starter Template

This is a comprehensive starter template for modern web applications built with Next.js. It's designed to be used as a starting point for any new web project requiring Next.js, providing a solid foundation with essential development tools and best practices pre-configured.

## What's Included

- **Next.js 16.3** - App Router, Turbopack (default bundler for dev and build)
- **React 19.3**
- **TypeScript 7** - Native `tsc` for type checking, with TypeScript 6 kept side-by-side for tooling (see below)
- **Tailwind CSS 4.3** - CSS-first config via `@tailwindcss/postcss`, no `tailwind.config`
- **shadcn/ui** - `base-nova` style on [Base UI](https://base-ui.com) primitives, `cn` class merging, lucide icons
- **ESLint 9** - Flat config with `eslint-config-next`
- **Husky** - Git hooks for automated quality checks
- **Commitlint** - Conventional commit message linting

## Requirements

- Node.js `>= 22.12` (required by commitlint 21)
- pnpm 10 (pinned via `packageManager`)

## Getting Started

### Installation

```bash
# Install dependencies
pnpm install

# Setup git hooks (required for pre-commit and commit-msg validation)
pnpm run setup:hooks
```

### Adding UI components

```bash
pnpm dlx shadcn@latest add button
```

Components are generated in `src/components/ui` using Base UI primitives (`@base-ui/react`). Theme tokens live in `src/app/globals.css`.

## TypeScript setup

TypeScript 7 does not ship a JavaScript compiler API yet, which `typescript-eslint` (used by `eslint-config-next`) and the Next.js editor plugin still need. Both versions are installed through npm aliases:

| Package name | Resolves to | Used by |
|---|---|---|
| `@typescript/native` | `typescript@7` | `tsc` binary: `pnpm typecheck` and `next build` |
| `typescript` | `@typescript/typescript6` | ESLint, shadcn CLI, editor (`tsc6` binary) |

Once TypeScript 7.1 ships its API and `typescript-eslint` supports it, drop the alias and install `typescript@^7` directly.

## Why ESLint 9

`eslint-config-next` depends on `eslint-plugin-react`, `eslint-plugin-import` and `eslint-plugin-jsx-a11y`, which do not support ESLint 10 yet. Stay on ESLint 9 until `eslint-config-next` supports it.

## Quality Assurance Features

### Git Hooks (Husky)
- **Pre-commit hook**: Runs linting and type checking before commits
- **Commit-msg hook**: Validates commit messages using conventional commit format

**Setup hooks after cloning:**
```bash
pnpm run setup:hooks
# or manually:
./setup-hooks.sh
```

### Scripts
- `pnpm run validate` - Runs both linting and type checking
- `pnpm run typecheck` - Generates Next.js route types, then runs TypeScript type checking
- `pnpm run lint` - ESLint code linting
- `pnpm run setup:hooks` - Setup Husky git hooks
