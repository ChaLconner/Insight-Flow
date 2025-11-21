import js from "@eslint/js";
import typescript from "typescript-eslint";
import react from "eslint-plugin-react";
import reactHooks from "eslint-plugin-react-hooks";

export default typescript.config(
  js.configs.recommended,
  ...typescript.configs.recommended,
  {
    files: ["**/*.{ts,tsx}"],
    plugins: {
      "react": react,
      "react-hooks": reactHooks,
    },
    languageOptions: {
      parser: typescript.parser,
      parserOptions: {
        ecmaFeatures: {
          jsx: true,
        },
        project: './tsconfig.json',
        tsconfigRootDir: import.meta.dirname,
      },
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      "react/react-in-jsx-scope": "off",
      
      // TypeScript recommended rules
      "@typescript-eslint/no-unused-vars": ["warn", { 
        "argsIgnorePattern": "^_",
        "varsIgnorePattern": "^_",
        "caughtErrorsIgnorePattern": "^_"
      }],
      "@typescript-eslint/no-explicit-any": "warn",
      "@typescript-eslint/no-non-null-assertion": "warn",
      "@typescript-eslint/prefer-nullish-coalescing": "warn",
      "@typescript-eslint/prefer-optional-chain": "warn",
      "@typescript-eslint/strict-boolean-expressions": "off", // Too strict for real-world usage
      
      // Store and state management specific rules
      "@typescript-eslint/consistent-type-imports": "error",
      "@typescript-eslint/prefer-readonly": "warn",
      
      // General coding standards
      "prefer-const": "error",
      "no-var": "error",
      "no-console": "off",
      "eqeqeq": ["error", "always", { "null": "never" }],
      "curly": ["error", "all"],
      "no-useless-escape": "error",
      
      // Interface and type definition rules
      "@typescript-eslint/no-empty-interface": "error",
    },
  },
  {
    files: ["src/stores/**/*.{ts,tsx}"],
    rules: {
      // Zustand store specific rules - more relaxed for stores
      "@typescript-eslint/no-unsafe-assignment": "off", // Allow in store actions
      "@typescript-eslint/no-explicit-any": "off", // Allow any in store selectors/actions
      "@typescript-eslint/strict-boolean-expressions": "off", // Allow loose checks in stores
      "@typescript-eslint/explicit-function-return-type": "off", // Don't require return types for store actions
      "@typescript-eslint/explicit-module-boundary-types": "off", // Don't require explicit types for exports
      "@typescript-eslint/prefer-nullish-coalescing": "off", // Allow || operator in stores
      "@typescript-eslint/no-non-null-assertion": "off", // Allow ! operator in stores
      "@typescript-eslint/consistent-type-imports": "off", // Relaxed for stores
    },
  },
  {
    files: ["src/types/**/*.{ts,tsx}"],
    rules: {
      // Type definitions specific rules
      "@typescript-eslint/no-empty-interface": "error",
      "@typescript-eslint/explicit-function-return-type": "off", // Interface methods don't need return types
      "@typescript-eslint/explicit-module-boundary-types": "off", // Export types don't need explicit types
      "@typescript-eslint/no-unsafe-assignment": "off", // Allow assignments in type definitions
      "@typescript-eslint/no-explicit-any": "off", // Allow any in type definitions when needed
      "@typescript-eslint/consistent-type-imports": "off", // Relaxed for type files
    },
  },
  {
    files: ["next.config.js"],
    languageOptions: {
      globals: {
        process: "readonly",
        __dirname: "readonly",
        module: "readonly"
      }
    }
  },
  {
    ignores: [
      "**/.next/**",
      "**/out/**",
      "**/build/**",
      "**/node_modules/**",
      "**/next-env.d.ts",
    ],
  }
);