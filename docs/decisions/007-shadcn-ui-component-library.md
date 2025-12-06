# ADR-007: Shadcn/ui Component Library

## Status

Accepted

## Date

2025-12-06

## Context

The Trading Algorithm Document Analyzer requires a frontend component library for building the React-based user interface (see ADR-002). The application needs:

- Accessible, production-ready UI components
- Flexibility for enterprise customization
- Modern, professional appearance
- Integration with React and TypeScript
- Maintainable, ownable code

Three major options were evaluated: Radix UI (headless primitives), Shadcn/ui (styled Radix components), and Material UI (comprehensive design system).

## Decision

We will use **Shadcn/ui** as the frontend component library.

Shadcn/ui is a collection of reusable components built on top of Radix UI primitives and styled with Tailwind CSS. Unlike traditional npm packages, components are copied directly into the codebase, giving full ownership and customization control.

### Implementation Details

- Components will be installed via the shadcn CLI
- Tailwind CSS will be used for styling
- Components reside in `src/components/ui/`
- Custom theme configuration in `tailwind.config.js`

## Consequences

### Positive

- **Full Code Ownership**: Components live in our codebase, enabling unlimited customization
- **Accessibility Built-in**: Radix primitives provide WAI-ARIA compliance
- **Modern Stack**: Tailwind CSS integration aligns with current best practices
- **No Version Lock-in**: No external package dependencies for UI components
- **Small Bundle Size**: Only include components actually used
- **TypeScript Support**: Full type safety out of the box

### Negative

- **Tailwind Requirement**: Must adopt Tailwind CSS for styling
- **Manual Updates**: Component updates require manual re-copying and merging
- **Fewer Components**: Smaller component set than Material UI
- **Learning Curve**: Team must learn Tailwind utility classes

### Neutral

- Components are based on Radix UI, a mature headless library
- Growing community and ecosystem support
- Works well with Next.js and Vite

## Alternatives Considered

### Radix UI (Headless)

Pure unstyled primitives requiring complete custom styling. While offering maximum flexibility, the additional effort to style every component from scratch was deemed excessive for project timelines. Shadcn/ui provides sensible defaults on top of Radix.

### Material UI (MUI)

The most comprehensive React component library with extensive documentation. Rejected due to:
- Opinionated Material Design aesthetic that may not align with enterprise branding
- Larger bundle size
- Customization often requires fighting the library's defaults
- Theming complexity for non-Material designs

## References

- [Shadcn/ui Documentation](https://ui.shadcn.com/)
- [Radix UI Primitives](https://www.radix-ui.com/)
- [Tailwind CSS](https://tailwindcss.com/)
- [ADR-002: React Frontend](002-react-frontend.md)
