interface AuthStatusIconProps {
  tone: "success" | "error";
}

const ICON_PATHS = {
  success: "M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z",
  error: "M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z",
} as const;

const TONE_CLASSES = {
  success: "text-green-500",
  error: "text-red-500",
} as const;

export function AuthStatusIcon({ tone }: Readonly<AuthStatusIconProps>) {
  return (
    <svg
      className={`mx-auto h-12 w-12 ${TONE_CLASSES[tone]}`}
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d={ICON_PATHS[tone]}
      />
    </svg>
  );
}
