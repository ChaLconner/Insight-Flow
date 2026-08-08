# ADR-0003: Zustand for Frontend State Management

## Status

Accepted

## Date

2026-01-02

## Context

The Next.js frontend requires a state management solution for:
- Global authentication state
- Notification state with real-time updates
- Theme preferences with persistence
- App-wide settings

The team evaluated multiple options considering:
- Bundle size impact
- Server-side rendering (SSR) compatibility
- Developer experience and boilerplate
- TypeScript support

## Decision

Use **Zustand** as the primary state management library with:
- **Persist middleware** for localStorage sync (auth, theme)
- **Selector pattern** for optimized re-renders
- **Separate stores** for different domains (auth, notifications, theme)
- **Actions pattern** for complex state mutations

### Store Architecture

```
stores/
├── auth-store.ts       # User authentication state
├── auth-actions.ts     # Login, logout, refresh actions
├── notification-store.ts
├── notification-selectors.ts
├── theme-store.ts
└── app-store.ts        # Global app state
```

## Consequences

### Positive

- Minimal bundle size (~2KB vs Redux ~10KB)
- No boilerplate (no reducers, action creators)
- First-class TypeScript support
- Built-in persistence middleware
- Works seamlessly with SSR/hydration
- Simple API reduces cognitive load

### Negative

- Less structured than Redux (requires discipline)
- No built-in devtools (uses Redux DevTools extension)
- Smaller community than Redux

### Neutral

- Team needs to adopt selector pattern for performance
- State is mutable (different paradigm than Redux)

## Alternatives Considered

### Alternative 1: Redux Toolkit

Rejected because:
- Larger bundle size for simple state needs
- More boilerplate even with RTK
- Overkill for current requirements

### Alternative 2: Jotai

Considered but rejected because:
- Atom-based model less intuitive for team
- Better for fine-grained reactivity we don't need
- Zustand's selector pattern sufficient

### Alternative 3: React Context + useReducer

Rejected because:
- Performance issues with frequent updates
- Requires manual optimization (useMemo, useCallback)
- No built-in persistence

## References

- [Zustand Documentation](https://github.com/pmndrs/zustand)
- [Zustand Persist Middleware](https://docs.pmnd.rs/zustand/integrations/persisting-store-data)
- [State Management Comparison](https://blog.logrocket.com/zustand-vs-redux/)
