"use client";

import { useGoogleLogin } from "@react-oauth/google";
import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { apiClient } from "@/lib/api-client";
import { API_CONFIG } from "@/lib/constants";
import { authActions } from "@/stores/auth-actions";
import {
  Mail,
  Lock,
  User,
  Eye,
  EyeOff,
  Github,
  Chrome,
  ArrowRight,
  Loader2,
  Check,
  X
} from "lucide-react";
import { toast } from "sonner";
import { getErrorMessage } from "@/lib/error-utils";

export default function RegisterPage() {
  const router = useRouter();
  const [formData, setFormData] = useState({
    firstName: "",
    lastName: "",
    email: "",
    username: "",
    password: "",
    confirmPassword: ""
  });
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [acceptTerms, setAcceptTerms] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [apiError, setApiError] = useState<string>("");

  const passwordRequirements = [
    { label: "At least 8 characters", test: (pwd: string) => pwd.length >= 8 },
    { label: "Contains uppercase letter", test: (pwd: string) => /[A-Z]/.test(pwd) },
    { label: "Contains lowercase letter", test: (pwd: string) => /[a-z]/.test(pwd) },
    { label: "Contains number", test: (pwd: string) => /\d/.test(pwd) },
    { label: "Contains special character", test: (pwd: string) => /[!@#$%^&*(),.?":{}|<>]/.test(pwd) },
  ];

  const validateForm = () => {
    const newErrors: Record<string, string> = {};

    if (!formData.firstName.trim()) { newErrors.firstName = "First name is required"; }
    if (!formData.lastName.trim()) { newErrors.lastName = "Last name is required"; }
    if (!formData.email.trim()) { newErrors.email = "Email is required"; }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) { newErrors.email = "Invalid email format"; }
    if (!formData.username.trim()) { newErrors.username = "Username is required"; }
    if (formData.username.length < 3) { newErrors.username = "Username must be at least 3 characters"; }
    if (!formData.password) { newErrors.password = "Password is required"; }
    if (!passwordRequirements.every(req => req.test(formData.password))) {
      newErrors.password = "Password doesn't meet requirements";
    }
    if (!formData.confirmPassword) { newErrors.confirmPassword = "Please confirm your password"; }
    if (formData.password !== formData.confirmPassword) { newErrors.confirmPassword = "Passwords don't match"; }
    if (!acceptTerms) { newErrors.terms = "You must accept terms and conditions"; }

    return newErrors;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setErrors({});
    setApiError("");

    const validationErrors = validateForm();
    if (Object.keys(validationErrors).length > 0) {
      setErrors(validationErrors);
      setIsLoading(false);
      return;
    }

    try {
      // Prepare data for backend API
      // Backend UserCreate schema expects: email, name, password (optional), google_id (optional)
      const name = `${formData.firstName.trim()} ${formData.lastName.trim()}`;

      // Transform frontend data to match backend UserCreate schema
      const backendUserData = {
        email: formData.email.trim(),
        name: name,
        password: formData.password
      };

      const { data } = await apiClient.post('/auth/register', backendUserData);

      // Registration successful - redirect to login
      toast.success("Account created successfully", {
        description: "Please sign in with your new account.",
      });
      router.push("/auth/login");
    } catch (error: any) {
      console.error("Registration error:", error);

      // Handle API errors
      let errorMessage = "";
      if (error.response?.data?.detail) {
        errorMessage = error.response.data.detail;
      } else if (error.response?.data?.message) {
        errorMessage = error.response.data.message;
      } else if (error.message) {
        errorMessage = error.message;
      } else {
        errorMessage = "Registration failed. Please try again.";
      }
      setApiError(errorMessage);
      toast.error("Registration failed", { description: errorMessage });
    } finally {
      setIsLoading(false);
    }
  };

  const handleGoogleLogin = useGoogleLogin({
    onSuccess: async (tokenResponse) => {
      try {
        setIsLoading(true);
        setApiError("");


        // Call backend API with Google token
        const response = await fetch(`${API_CONFIG.BASE_URL}/auth/google`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            access_token: tokenResponse.access_token,
          }),
        });

        if (!response.ok) {
          throw new Error('Google login failed');
        }

        const data = await response.json();


        toast.success(`Welcome ${data.user.firstName || 'User'}!`, {
          description: "Successfully signed in with Google.",
        });

        await authActions.loginWithResponse(data);

        const user = data.user;
        let redirectUrl = "/dashboard";

        if (user?.role) {
          switch (user.role) {
            case 'admin': redirectUrl = "/dashboard"; break;
            case 'manager': redirectUrl = "/projects"; break;
            case 'member':
            case 'user': redirectUrl = "/projects?tab=tasks"; break;
            case 'viewer': redirectUrl = "/projects"; break;
            default: redirectUrl = "/dashboard";
          }
        }

        router.push(redirectUrl);
      } catch (error) {
        console.error('❌ Google login error:', error);
        setApiError('Google login failed. Please try again.');
        toast.error("Google login failed", { description: getErrorMessage(error) });
      } finally {
        setIsLoading(false);
      }
    },
    onError: () => {
      console.error('❌ Google login failed');
      setApiError('Google login failed. Please try again.');
      setIsLoading(false);
      toast.error("Google login failed");
    },
    flow: 'implicit',
  });

  const handleInputChange = (field: string, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: "" }));
    }
    // Clear API error when user makes changes
    if (apiError) {
      setApiError("");
    }
  };

  const isPasswordValid = (requirement: any) => requirement.test(formData.password);
  const isFormValid = Object.keys(validateForm()).length === 0;

  return (
    <div className="min-h-screen bg-gradient-to-br from-zinc-900 via-zinc-800 to-indigo-900 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="mx-auto h-12 w-12 rounded-xl bg-indigo-600 flex items-center justify-center mb-4 shadow-lg shadow-indigo-500/25">
            <span className="text-2xl font-bold text-white">IF</span>
          </div>
          <h1 className="text-2xl font-bold text-white mb-2">Create your account</h1>
          <p className="text-zinc-400">Join Insight Flow and start managing projects</p>
        </div>

        <Card className="border-white/10 bg-white/5 backdrop-blur-xl shadow-2xl">
          <CardHeader className="space-y-1 pb-6">
            <CardTitle className="text-xl text-white text-center">Sign up</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* API Error Display */}
            {apiError && (
              <div className="bg-red-500/10 border border-red-500/20 rounded-md p-3">
                <p className="text-sm text-red-400">{apiError}</p>
              </div>
            )}

            {/* Social Login */}
            <div className="space-y-3">
              <Button
                variant="outline"
                className="w-full border-white/10 bg-white/5 text-white hover:bg-white/10 transition-colors"
                onClick={() => handleGoogleLogin()}
                disabled={isLoading || !process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID}
                title={!process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID ? "Google Client ID is missing" : "Sign up with Google"}
              >
                <Chrome className="h-4 w-4 mr-3" />
                Continue with Google
              </Button>
              <Button
                variant="outline"
                className="w-full border-white/10 bg-white/5 text-white hover:bg-white/10 transition-colors"
                onClick={() => {
                  const clientId = process.env.NEXT_PUBLIC_GITHUB_CLIENT_ID;
                  if (!clientId) {
                    toast.error("GitHub signup not configured", {
                      description: "GitHub Client ID is missing",
                    });
                    return;
                  }
                  const redirectUri = encodeURIComponent(
                    `${window.location.origin}/auth/callback/github`
                  );
                  const scope = "read:user user:email";
                  window.location.href = `https://github.com/login/oauth/authorize?client_id=${clientId}&redirect_uri=${redirectUri}&scope=${scope}`;
                }}
                disabled={isLoading || !process.env.NEXT_PUBLIC_GITHUB_CLIENT_ID}
                title={!process.env.NEXT_PUBLIC_GITHUB_CLIENT_ID ? "GitHub Client ID is missing" : "Sign up with GitHub"}
              >
                <Github className="h-4 w-4 mr-3" />
                Continue with GitHub
              </Button>
            </div>

            {/* Divider */}
            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-white/10" />
              </div>
              <div className="relative flex justify-center text-xs uppercase">
                <span className="bg-zinc-900 px-2 text-zinc-400">Or continue with</span>
              </div>
            </div>

            {/* Register Form */}
            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Name Fields */}
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-2">
                  <Label htmlFor="firstName" className="text-zinc-300">First Name</Label>
                  <Input
                    id="firstName"
                    placeholder="John"
                    value={formData.firstName}
                    onChange={(e) => handleInputChange("firstName", e.target.value)}
                    className={`bg-white/5 border-white/10 text-white placeholder:text-zinc-400 ${errors.firstName ? "border-red-500" : ""
                      }`}
                    disabled={isLoading}
                  />
                  {errors.firstName && (
                    <p className="text-xs text-red-400">{errors.firstName}</p>
                  )}
                </div>
                <div className="space-y-2">
                  <Label htmlFor="lastName" className="text-zinc-300">Last Name</Label>
                  <Input
                    id="lastName"
                    placeholder="Doe"
                    value={formData.lastName}
                    onChange={(e) => handleInputChange("lastName", e.target.value)}
                    className={`bg-white/5 border-white/10 text-white placeholder:text-zinc-400 ${errors.lastName ? "border-red-500" : ""
                      }`}
                    disabled={isLoading}
                  />
                  {errors.lastName && (
                    <p className="text-xs text-red-400">{errors.lastName}</p>
                  )}
                </div>
              </div>

              {/* Email */}
              <div className="space-y-2">
                <Label htmlFor="email" className="text-zinc-300">Email</Label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-zinc-400" />
                  <Input
                    id="email"
                    type="email"
                    placeholder="john@example.com"
                    value={formData.email}
                    onChange={(e) => handleInputChange("email", e.target.value)}
                    className={`pl-10 bg-white/5 border-white/10 text-white placeholder:text-zinc-400 ${errors.email ? "border-red-500" : ""
                      }`}
                    disabled={isLoading}
                  />
                </div>
                {errors.email && (
                  <p className="text-xs text-red-400">{errors.email}</p>
                )}
              </div>

              {/* Username */}
              <div className="space-y-2">
                <Label htmlFor="username" className="text-zinc-300">Username</Label>
                <div className="relative">
                  <User className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-zinc-400" />
                  <Input
                    id="username"
                    placeholder="johndoe"
                    value={formData.username}
                    onChange={(e) => handleInputChange("username", e.target.value)}
                    className={`pl-10 bg-white/5 border-white/10 text-white placeholder:text-zinc-400 ${errors.username ? "border-red-500" : ""
                      }`}
                    disabled={isLoading}
                  />
                </div>
                {errors.username && (
                  <p className="text-xs text-red-400">{errors.username}</p>
                )}
              </div>

              {/* Password */}
              <div className="space-y-2">
                <Label htmlFor="password" className="text-zinc-300">Password</Label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-zinc-400" />
                  <Input
                    id="password"
                    type={showPassword ? "text" : "password"}
                    placeholder="Create a strong password"
                    value={formData.password}
                    onChange={(e) => handleInputChange("password", e.target.value)}
                    className={`pl-10 pr-10 bg-white/5 border-white/10 text-white placeholder:text-zinc-400 ${errors.password ? "border-red-500" : ""
                      }`}
                    disabled={isLoading}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 transform -translate-y-1/2 text-zinc-400 hover:text-white"
                    disabled={isLoading}
                  >
                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>

                {/* Password Requirements */}
                {formData.password && (
                  <div className="mt-2 space-y-1">
                    {passwordRequirements.map((req, index) => (
                      <div key={index} className="flex items-center gap-2 text-xs">
                        {isPasswordValid(req) ? (
                          <Check className="h-3 w-3 text-emerald-400" />
                        ) : (
                          <X className="h-3 w-3 text-zinc-500" />
                        )}
                        <span className={isPasswordValid(req) ? "text-emerald-400" : "text-zinc-500"}>
                          {req.label}
                        </span>
                      </div>
                    ))}
                  </div>
                )}

                {errors.password && (
                  <p className="text-xs text-red-400">{errors.password}</p>
                )}
              </div>

              {/* Confirm Password */}
              <div className="space-y-2">
                <Label htmlFor="confirmPassword" className="text-zinc-300">Confirm Password</Label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-zinc-400" />
                  <Input
                    id="confirmPassword"
                    type={showConfirmPassword ? "text" : "password"}
                    placeholder="Confirm your password"
                    value={formData.confirmPassword}
                    onChange={(e) => handleInputChange("confirmPassword", e.target.value)}
                    className={`pl-10 pr-10 bg-white/5 border-white/10 text-white placeholder:text-zinc-400 ${errors.confirmPassword ? "border-red-500" : ""
                      }`}
                    disabled={isLoading}
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    className="absolute right-3 top-1/2 transform -translate-y-1/2 text-zinc-400 hover:text-white"
                    disabled={isLoading}
                  >
                    {showConfirmPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
                {errors.confirmPassword && (
                  <p className="text-xs text-red-400">{errors.confirmPassword}</p>
                )}
              </div>

              {/* Terms and Conditions */}
              <div className="space-y-2">
                <label className="flex items-start gap-3">
                  <input
                    type="checkbox"
                    checked={acceptTerms}
                    onChange={(e) => setAcceptTerms(e.target.checked)}
                    className="mt-1 rounded border-white/10 bg-white/5 text-indigo-600 focus:ring-indigo-500 focus:ring-offset-0"
                    disabled={isLoading}
                  />
                  <span className="text-sm text-zinc-400">
                    I agree to{" "}
                    <Link href="/terms" className="text-indigo-400 hover:text-indigo-300">
                      Terms of Service
                    </Link>{" "}
                    and{" "}
                    <Link href="/privacy" className="text-indigo-400 hover:text-indigo-300">
                      Privacy Policy
                    </Link>
                  </span>
                </label>
                {errors.terms && (
                  <p className="text-xs text-red-400">{errors.terms}</p>
                )}
              </div>

              <Button
                type="submit"
                className="w-full bg-indigo-600 hover:bg-indigo-500 text-white font-medium py-2.5"
                disabled={isLoading || !isFormValid}
              >
                {isLoading ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <>
                    Create Account
                    <ArrowRight className="h-4 w-4 ml-2" />
                  </>
                )}
              </Button>
            </form>
          </CardContent>
        </Card>

        {/* Footer */}
        <p className="text-center text-sm text-zinc-400 mt-6">
          Already have an account?{" "}
          <Link
            href="/auth/login"
            className="text-indigo-400 hover:text-indigo-300 font-medium transition-colors"
          >
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}