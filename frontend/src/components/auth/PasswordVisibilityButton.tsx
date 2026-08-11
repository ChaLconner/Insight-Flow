import { Eye, EyeOff } from "lucide-react";

interface PasswordVisibilityButtonProps {
  isVisible: boolean;
  onToggle: () => void;
  disabled?: boolean;
}

export function PasswordVisibilityButton({
  isVisible,
  onToggle,
  disabled,
}: Readonly<PasswordVisibilityButtonProps>) {
  const label = isVisible ? "Hide password" : "Show password";

  return (
    <button
      type="button"
      onClick={onToggle}
      className="absolute right-3 top-1/2 transform -translate-y-1/2 text-muted-foreground hover:text-foreground"
      disabled={disabled}
      title={label}
      aria-label={label}
    >
      {isVisible ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
    </button>
  );
}
