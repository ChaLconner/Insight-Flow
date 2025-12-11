import { GoogleAuthProvider } from "@/providers/google-auth-provider";

export default function AuthLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <GoogleAuthProvider>
            {children}
        </GoogleAuthProvider>
    );
}
