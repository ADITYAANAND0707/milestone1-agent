## Project Overview

This is an **Untitled UI React** component library project built with:

- **React 19.1.1** with TypeScript
- **Tailwind CSS v4.1** for styling
- **React Aria Components** as the foundation for accessibility and behavior

## Key Architecture Principles

### Component Foundation

- All components are built on **React Aria Components** for consistent accessibility and behavior
- Components follow the compound component pattern with sub-components (e.g., `Select.Item`, `Select.ComboBox`)
- TypeScript is used throughout for type safety

### Import Naming Convention

**CRITICAL**: All imports from `react-aria-components` must be prefixed with `Aria*` for clarity and consistency:

```typescript
// ✅ Correct
import { Button as AriaButton, TextField as AriaTextField } from "react-aria-components";
// ❌ Incorrect
import { Button, TextField } from "react-aria-components";
```

This convention:

- Prevents naming conflicts with custom components
- Makes it clear when using base React Aria components
- Maintains consistency across the entire codebase

### File Naming Convention

**IMPORTANT**: All files must be named in **kebab-case** for consistency:

```
✅ Correct:
- date-picker.tsx
- user-profile.tsx
- api-client.ts
- auth-context.tsx

❌ Incorrect:
- DatePicker.tsx
- userProfile.tsx
- apiClient.ts
- AuthContext.tsx
```

This applies to all file types including:

- Component files (.tsx, .jsx)
- TypeScript/JavaScript files (.ts, .js)
- Style files (.css, .scss)
- Test files (.test.ts, .spec.tsx)
- Configuration files (when creating new ones)

## Development Commands

```bash
# Development
npm run dev               # Start Vite development server (http://localhost:5173)
npm run build            # Build for production (TypeScript compilation + Vite build)
```

## Project Structure

### Application Architecture

```
src/
├── components/
│   ├── base/              # Core UI components (Button, Input, Select, etc.)
│   ├── application/       # Complex application components
│   ├── foundations/       # Design tokens and foundational elements
│   ├── marketing/         # Marketing-specific components
│   └── shared-assets/     # Reusable assets and illustrations
├── hooks/                 # Custom React hooks
├── pages/                 # Route components
├── providers/             # React context providers
├── styles/               # Global styles and theme
├── types/                # TypeScript type definitions
└── utils/                # Utility functions
```

### Component Patterns

#### 1. Base Components

Located in `components/base/`, these are the building blocks:

- `Button` - All button variants with loading states
- `Input` - Text inputs with validation and icons
- `Select` - Dropdown selections with complex options
- `Checkbox`, `Radio`, `Toggle` - Form controls
- `Avatar`, `Badge`, `Tooltip` - Display components

#### 2. Application Components

Located in `components/application/`, these are complex UI patterns:

- `DatePicker` - Calendar-based date selection
- `Modal` - Overlay dialogs
- `Pagination` - Data navigation
- `Table` - Data display with sorting
- `Tabs` - Content organization

#### 3. Styling Architecture

- Uses a `sortCx` utility for organized style objects
- Follows size variants: `sm`, `md`, `lg`, `xl`
- Color variants: `primary`, `secondary`, `tertiary`, `destructive`, etc.
- Responsive and state-aware styling with Tailwind

#### 4. Component Props Pattern

```typescript
interface CommonProps {
    size?: "sm" | "md" | "lg";
    isDisabled?: boolean;
    isLoading?: boolean;
    // ... other common props
}

interface ButtonProps extends CommonProps, HTMLButtonElement {
    color?: "primary" | "secondary" | "tertiary";
    iconLeading?: FC | ReactNode;
    iconTrailing?: FC | ReactNode;
}
```

## Styling Guidelines

### Tailwind CSS v4.1

- Uses the latest Tailwind CSS v4.1 features
- Custom design tokens defined in theme configuration
- Consistent spacing, colors, and typography scales

### Brand Color Customization

To change the main brand color across the entire application:

1. **Update Brand Color Variables**: Edit `src/styles/theme.css` and modify the `--color-brand-*` variables
2. **Maintain Color Scale**: Ensure you provide a complete color scale from 25 to 950 with proper contrast ratios
3. **Example Brand Color Scale**:
    ```css
    --color-brand-25: rgb(252 250 255); /* Lightest tint */
    --color-brand-50: rgb(249 245 255);
    --color-brand-100: rgb(244 235 255);
    --color-brand-200: rgb(233 215 254);
    --color-brand-300: rgb(214 187 251);
    --color-brand-400: rgb(182 146 246);
    --color-brand-500: rgb(158 119 237); /* Base brand color */
    --color-brand-600: rgb(127 86 217); /* Primary interactive color */
    --color-brand-700: rgb(105 65 198);
    --color-brand-800: rgb(83 56 158);
    --color-brand-900: rgb(66 48 125);
    --color-brand-950: rgb(44 28 95); /* Darkest shade */
    ```

The color scale automatically adapts to both light and dark modes through the CSS variable system.

### Style Organization

```typescript
export const styles = sortCx({
    common: {
        root: "base-classes-here",
        icon: "icon-classes-here",
    },
    sizes: {
        sm: { root: "small-size-classes" },
        md: { root: "medium-size-classes" },
    },
    colors: {
        primary: { root: "primary-color-classes" },
        secondary: { root: "secondary-color-classes" },
    },
});
```

### Utility Functions

- `cx()` - Class name utility (from `@/utils/cx`)
- `sortCx()` - Organized style objects
- `isReactComponent()` - Component type checking

## Icon Usage

### Available Libraries

- `@untitledui/icons` - 1,100+ line-style icons (free)
- `@untitledui/file-icons` - File type icons
- `@untitledui-pro/icons` - 4,600+ icons in 4 styles (Requires PRO access)

### Import & Usage

```typescript
// Recommended: Named imports (tree-shakeable)
import { Home01, Settings01, ChevronDown } from "@untitledui/icons";

// Component props - pass as reference
<Button iconLeading={ChevronDown}>Options</Button>

// Standalone usage
<Home01 className="size-5 text-gray-600" />

// As JSX element - MUST include data-icon
<Button iconLeading={<ChevronDown data-icon className="size-4" />}>Options</Button>
```

### Styling

```typescript
// Size: use size-4 (16px), size-5 (20px), size-6 (24px)
<Home01 className="size-5" />

// Color: use semantic text colors
<Home01 className="size-5 text-brand-600" />

// Stroke width (line icons only)
<Home01 className="size-5" strokeWidth={2} />

// Accessibility: decorative icons need aria-hidden
<Home01 className="size-5" aria-hidden="true" />
```

### PRO Icon Styles

```typescript
import { Home01 } from "@untitledui-pro/icons";
// Line
import { Home01 } from "@untitledui-pro/icons/duocolor";
import { Home01 } from "@untitledui-pro/icons/duotone";
import { Home01 } from "@untitledui-pro/icons/solid";
```

## Form Handling

### Form Components

- `Input` - Text inputs with validation
- `Select` - Dropdown selections
- `Checkbox`, `Radio` - Selection controls
- `Textarea` - Multi-line text input
- `Form` - Form wrapper with validation

## Animation and Interactions

### Animation Libraries

- `motion` (Framer Motion) for complex animations
- `tailwindcss-animate` for utility-based animations
- CSS transitions for simple state changes

### CSS Transitions

For default small transition actions (hover states, color changes, etc.), use:

```typescript
className = "transition duration-100 ease-linear";
```

This provides a snappy 100ms linear transition that feels responsive without being jarring.

### Loading States

- Components support `isLoading` prop
- Built-in loading spinners
- Proper disabled states during loading

## Common Patterns

### Compound Components

```typescript
const Select = SelectComponent as typeof SelectComponent & {
    Item: typeof SelectItem;
    ComboBox: typeof ComboBox;
};
Select.Item = SelectItem;
Select.ComboBox = ComboBox;
```

### Conditional Rendering

```typescript
{label && <Label isRequired={isRequired}>{label}</Label>}
{hint && <HintText isInvalid={isInvalid}>{hint}</HintText>}
```

## State Management

### Component State

- Use React Aria's built-in state management
- Local state for component-specific data
- Context for shared component state (theme, router)

### Global State

- Theme context in `src/providers/theme.tsx`
- Router context in `src/providers/router-provider.tsx`

## Key Files and Utilities

### Core Utilities

- `src/utils/cx.ts` - Class name utilities
- `src/utils/is-react-component.ts` - Component type checking
- `src/hooks/` - Custom React hooks

### Style Configuration

- `src/styles/globals.css` - Global styles
- `src/styles/theme.css` - Theme definitions
- `src/styles/typography.css` - Typography styles

## Best Practices for AI Assistance

### When Adding New Components

1. Follow the existing component structure
2. Use React Aria Components as foundation
3. Implement proper TypeScript types
4. Add size and color variants where applicable
5. Include accessibility features
6. Follow the naming conventions
7. Add components to appropriate folders (`base/`, `application/`, etc.)

## Most Used Components Reference

### Button

The Button component is the most frequently used interactive element across the library.

**Import:**

```typescript
import { Button } from "@/components/base/buttons/button";
```

**Common Props:**

- `size`: `"sm" | "md" | "lg" | "xl"` - Button size (default: `"sm"`)
- `color`: `"primary" | "secondary" | "tertiary" | "link-gray" | "link-color" | "primary-destructive" | "secondary-destructive" | "tertiary-destructive" | "link-destructive"` - Button color variant (default: `"primary"`)
- `iconLeading`: `FC | ReactNode` - Icon or component to display before text
- `iconTrailing`: `FC | ReactNode` - Icon or component to display after text
- `isDisabled`: `boolean` - Disabled state
- `isLoading`: `boolean` - Loading state with spinner
- `showTextWhileLoading`: `boolean` - Keep text visible during loading
- `children`: `ReactNode` - Button content

**Examples:**

```typescript
// Basic button
<Button size="md">Save</Button>

// With leading icon
<Button iconLeading={Check} color="primary">Save</Button>

// Loading state
<Button isLoading showTextWhileLoading>Submitting...</Button>

// Destructive action
<Button color="primary-destructive" iconLeading={Trash02}>Delete</Button>
```

### Input

Text input component with extensive customization options.

**Import:**

```typescript
import { Input } from "@/components/base/input/input";
import { InputGroup } from "@/components/base/input/input-group";
```

**Common Props:**

- `size`: `"sm" | "md"` - Input size (default: `"sm"`)
- `label`: `string` - Field label
- `placeholder`: `string` - Placeholder text
- `hint`: `string` - Helper text below input
- `tooltip`: `string` - Tooltip text for help icon
- `icon`: `FC` - Leading icon component
- `isRequired`: `boolean` - Required field indicator
- `isDisabled`: `boolean` - Disabled state
- `isInvalid`: `boolean` - Error state

**Examples:**

```typescript
// Basic input with label
<Input label="Email" placeholder="olivia@untitledui.com" />

// With icon and validation
<Input
  icon={Mail01}
  label="Email"
  isRequired
  isInvalid
  hint="Please enter a valid email"
/>

// Input group with button
<InputGroup label="Website" trailingAddon={<Button>Copy</Button>}>
  <InputBase placeholder="www.untitledui.com" />
</InputGroup>
```

### Select

Dropdown selection component with search and multi-select capabilities.

**Import:**

```typescript
import { MultiSelect } from "@/components/base/select/multi-select";
import { Select } from "@/components/base/select/select";
```

**Common Props:**

- `size`: `"sm" | "md"` - Select size (default: `"sm"`)
- `label`: `string` - Field label
- `placeholder`: `string` - Placeholder text
- `hint`: `string` - Helper text
- `tooltip`: `string` - Tooltip text
- `items`: `Array` - Data items to display
- `isRe

... (truncated)