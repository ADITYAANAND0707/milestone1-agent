# Coding Guidelines

These guidelines are injected into the AI system prompt so all generated code follows team standards.

---

## 1. Component Standards

- Use **function components** with hooks — no class components
- Use **PascalCase** for component names (e.g., `LoginForm`, `DashboardCard`)
- Use **camelCase** for variables, functions, and props (e.g., `handleClick`, `isLoading`)
- Keep components **compact** — under 150 lines when possible
- One component per file / code block
- Always end generated code with `root.render(React.createElement(ComponentName));`

## 2. Styling

- Use **Tailwind CSS** utility classes exclusively — no inline styles, no CSS-in-JS
- Use **design tokens** from `tokens.json` for colors, spacing, typography, and border radius
- Follow the project color palette:
  - Primary/Blue: `blue-500` (#2E90FA) through `blue-700` (#175CD3)
  - Gray: `gray-50` (#F9FAFB) through `gray-900` (#101828)
  - Success: `emerald-500` (#12B76A) — use for positive status
  - Error: `red-500` (#F04438) — use for errors/destructive
  - Warning: `amber-500` (#F79009) — use for warnings
- Use responsive classes when generating layouts (`sm:`, `md:`, `lg:` prefixes)
- Dark mode: use `dark:` variant classes where appropriate

## 3. Accessibility

- All interactive elements must have clear **focus states** (`focus:ring-2 focus:ring-blue-500`)
- Use **semantic HTML** elements (`<nav>`, `<main>`, `<section>`, `<button>`, `<form>`)
- All images must have `alt` attributes
- Form inputs must have associated `<label>` elements
- Buttons must have descriptive text or `aria-label`
- Maintain sufficient color contrast (WCAG AA minimum)

## 4. Code Quality

- **No hardcoded values** — use design tokens for colors, spacing, typography
- **No import statements** in generated code (React/ReactDOM are global via CDN)
- Handle **loading states** — show spinners or skeleton screens
- Handle **error states** — display user-friendly error messages
- Handle **empty states** — show helpful messages when no data exists
- Use **destructuring** for props: `function Card({ title, description })`

## 5. Naming Conventions

| Item | Convention | Example |
|------|-----------|---------|
| Components | PascalCase | `UserProfile`, `BankSummaryCard` |
| Functions | camelCase | `handleSubmit`, `fetchData` |
| Constants | UPPER_SNAKE_CASE | `MAX_RETRIES`, `API_BASE_URL` |
| CSS classes | Tailwind utilities | `flex items-center gap-4` |
| Files | kebab-case or PascalCase | `user-profile.tsx` or `UserProfile.tsx` |
| Boolean props | `is`/`has`/`can` prefix | `isLoading`, `hasError`, `canEdit` |

## 6. Component Structure Pattern

Generated components should follow this order:

1. State declarations (`useState`, `useEffect`)
2. Event handlers
3. Helper / render functions
4. Return JSX

```jsx
function ComponentName({ prop1, prop2 }) {
  // 1. State
  const [value, setValue] = React.useState('');

  // 2. Handlers
  const handleChange = (e) => setValue(e.target.value);

  // 3. Return JSX
  return (
    <div className="flex flex-col gap-4 p-4">
      {/* Component content */}
    </div>
  );
}
root.render(React.createElement(ComponentName));
```

## 7. Design System Usage

- Reference components from `catalog.json` when applicable (Button, Input, Avatar, Badge, etc.)
- Use the component props as documented in the catalog
- Follow the Untitled UI design patterns and visual language
- Maintain visual consistency across all generated components

## 8. Performance

- Avoid unnecessary re-renders — memoize with `React.useMemo` and `React.useCallback` where appropriate
- Keep state as local as possible
- Avoid large inline objects or arrays in JSX (causes re-renders)

## 9. Variant Generation Rules

When generating multiple variants:
- Each variant must be a **separate, complete, standalone** component
- Use **different component names** for each variant (e.g., `CardMinimal`, `CardBold`)
- Each must end with its own `root.render(React.createElement(VariantName));`
- Label each with `## Variant N: StyleName` heading
- Keep each variant under 80 lines
