export function isE2ERuntime(): boolean {
  return (
    process.env.NEXT_PUBLIC_E2E === "1" ||
    process.env.NEXT_PUBLIC_E2E === "true"
  );
}

export function shouldEnableDevelopmentDiagnostics(): boolean {
  return process.env.NODE_ENV === "development" && !isE2ERuntime();
}

