# shadcn/ui monorepo template

This is a Vite monorepo template with shadcn/ui.

## Adding components

To add components to your app, run the following command at the root of your `web` app:

```bash
pnpm dlx shadcn@latest add button -c apps/web
```

This will place the ui components in the `packages/ui/src/components` directory.

## Using components

To use the components in your app, import them from the `ui` package.

```tsx
import { Button } from "@workspace/ui/components/button";
```
oguzardaorhan@Oguzarda-MacBook-Air app-ui-kit % cat .gitignore
# Logs
logs
*.log
npm-debug.log*
yarn-debug.log*
yarn-error.log*
.pnpm-debug.log*
lerna-debug.log*

node_modules
dist
dist-ssr
*.local

# env files (can opt-in for committing if needed)
.env*

# turbo
.turbo

# Editor directories and files
.vscode/*
!.vscode/extensions.json
.idea
.DS_Store
*.suo
*.ntvs*
*.njsproj
*.sln
*.sw?

# typescript
*.tsbuildinfo

*storybook.log
storybook-static