"use client";

import { useGoogleLogin } from "@react-oauth/google";
import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { AnimatedBackground, FloatingShapes } from "@/components/ui/animated-background";
import { API_CONFIG } from "@/lib/constants";
import { authActions } from "@/stores/auth-actions";
import { User } from "@/types";
import {
  Mail,
  Lock,
  Eye,
  EyeOff,
  Github,
  Chrome,
  ArrowRight,
  Loader2
} from "lucide-react";

export default function LoginPage() {
  const router = useRouter();
  const [formData, setFormData] = useState({
    email: "",
    password: ""
  });
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setErrors({});

    // Validation
    const newErrors: Record<string, string> = {};
    if (!formData.email) { newErrors.email = "Email is required"; }
    if (!formData.password) { newErrors.password = "Password is required"; }

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      setIsLoading(false);
      return;
    }

    try {
      console.log('🔄 Starting login process...');

      // Call backend API
      console.log('📡 Calling login API...');
      console.log('📧 Email:', formData.email);
      console.log('🔑 Password length:', formData.password.length);
      console.log('🌐 API Base URL:', API_CONFIG.BASE_URL);

      const response = await fetch(`${API_CONFIG.BASE_URL}/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: formData.email,
          password: formData.password,
        }),
      });

      console.log('📨 Login response status:', response.status);
      console.log('📨 Login response headers:', Array.from(response.headers.entries()));

      if (!response.ok) {
        let errorData;
        try {
          errorData = await response.json();
          console.error('❌ Login response error data:', errorData);
        } catch (parseError) {
          console.error('❌ Failed to parse error response:', parseError);
          // If JSON parsing fails, use default error
          errorData = { detail: 'Login failed' };
        }
        console.error('❌ Login failed:', errorData);
        throw new Error(errorData?.detail ?? 'Login failed');
      }

      const data = await response.json();
      console.log('✅ Login successful, received data:', data);
      console.log('🔍 Login response structure:', {
        hasAccessToken: !!data.access_token,
        hasRefreshToken: !!data.refresh_token,
        hasUser: !!data.user,
        dataKeys: Object.keys(data),
        expectedUserKeys: ['id', 'email', 'name', 'role']
      });

      // Use authActions to properly handle login
      await authActions.loginWithResponse(data);

      // Get the user data from the store after login
      const user = data.user;

      console.log('🚀 Redirecting to appropriate page based on user role...');
      console.log('👤 User object after login:', user);
      console.log('🔑 User role:', user?.role);

      // Determine redirect URL based on user role with better fallbacks
      let redirectUrl = "/dashboard"; // Default redirect to dashboard

      if (user?.role) {
        switch (user.role) {
          case 'admin':
            redirectUrl = "/dashboard"; // Admins go to main dashboard
            break;
          case 'manager':
            redirectUrl = "/projects"; // Managers go to projects page
            break;
          case 'member':
          case 'user':
            redirectUrl = "/projects?tab=tasks"; // Regular users go to tasks page
            break;
          case 'viewer':
            redirectUrl = "/projects"; // Viewers go to projects page
            break;
          default:
            redirectUrl = "/dashboard"; // Default to dashboard
        }
      } else {
        console.log('⚠️ No user role found, defaulting to dashboard');
        redirectUrl = "/dashboard"; // Default for users without role
      }

      // Redirect to appropriate page based on user role
      // Add small delay to allow state to settle and prevent routing conflicts
      setTimeout(() => {
        if (typeof window !== 'undefined') {
          // Use router.push for client-side navigation with delay
          window.location.href = redirectUrl;
        }
      }, 100);

    } catch (error) {
      console.error('❌ Login error:', error);
      console.error('❌ Login error details:', {
        message: error instanceof Error ? error.message : 'Unknown error',
        stack: error instanceof Error ? error.stack : 'No stack trace',
        name: error instanceof Error ? error.name : 'Unknown'
      });
      setErrors({ password: "Invalid email or password" });
    } finally {
      setIsLoading(false);
    }
  };

  const handleGoogleLogin = useGoogleLogin({
    onSuccess: async (tokenResponse) => {
      try {
        setIsLoading(true);
        console.log('🔄 Starting Google login process...');

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
        console.log('✅ Google login successful');

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

        // Use window.location.href for consistency
        window.location.href = redirectUrl;
      } catch (error) {
        console.error('❌ Google login error:', error);
        setErrors({ submit: 'Google login failed. Please try again.' });
      } finally {
        setIsLoading(false);
      }
    },
    onError: () => {
      console.error('❌ Google login failed');
      setErrors({ submit: 'Google login failed. Please try again.' });
      setIsLoading(false);
    },
    flow: 'implicit',
  });

  const handleInputChange = (field: string, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: "" }));
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-zinc-900 via-zinc-800 to-indigo-900 flex items-center justify-center p-4 relative overflow-hidden">
      {/* Animated Background Components */}
      <AnimatedBackground />
      <FloatingShapes />

      <div className="w-full max-w-md relative z-20">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="mx-auto h-12 w-12 rounded-xl bg-indigo-600 flex items-center justify-center mb-4 shadow-lg shadow-indigo-500/25">
            <span className="text-2xl font-bold text-white">IF</span>
          </div>
          <h1 className="text-2xl font-bold text-white mb-2">Welcome back</h1>
          <p className="text-zinc-400">Sign in to your Insight Flow account</p>
        </div>

        <Card className="bg-white/5 backdrop-blur-xl shadow-2xl border-0">
          <CardHeader className="space-y-1 pb-6">
            <CardTitle className="text-xl text-white text-center">Sign in</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Social Login */}
            <div className="space-y-3">
              <Button
                variant="outline"
                className="w-full border-white/10 bg-white/5 text-white hover:bg-white/10 transition-colors"
                onClick={() => handleGoogleLogin()}
                disabled={isLoading || !process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID}
                title={!process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID ? "Google Client ID is missing" : "Sign in with Google"}
              >
                <Chrome className="h-4 w-4 mr-3" />
                Continue with Google
              </Button>
              <Button
                variant="outline"
                className="w-full border-white/10 bg-white/5 text-white hover:bg-white/10 transition-colors"
                onClick={() => {/* Handle GitHub login */ }}
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

            {/* Login Form */}
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="email" className="text-zinc-300">Email</Label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-zinc-400" />
                  <Input
                    id="email"
                    type="email"
                    placeholder="Enter your email"
                    value={formData.email}
                    onChange={(e) => handleInputChange("email", e.target.value)}
                    className={`pl-10 bg-white/5 border-white/10 text-white placeholder:text-zinc-400 ${errors.email ? "border-red-500" : ""
                      }`}
                    disabled={isLoading}
                  />
                </div>
                {errors.email && (
                  <p className="text-sm text-red-400">{errors.email}</p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="password" className="text-zinc-300">Password</Label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-zinc-400" />
                  <Input
                    id="password"
                    type={showPassword ? "text" : "password"}
                    placeholder="Enter your password"
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
                {errors.password && (
                  <p className="text-sm text-red-400">{errors.password}</p>
                )}
              </div>

              <div className="flex items-center justify-between">
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    className="rounded border-white/10 bg-white/5 text-indigo-600 focus:ring-indigo-500 focus:ring-offset-0"
                  />
                  <span className="ml-2 text-sm text-zinc-400">Remember me</span>
                </label>
                <Link
                  href="/auth/forgot-password"
                  className="text-sm text-indigo-400 hover:text-indigo-300 transition-colors"
                >
                  Forgot password?
                </Link>
              </div>

              <Button
                type="submit"
                className="w-full bg-indigo-600 hover:bg-indigo-500 text-white font-medium py-2.5"
                disabled={isLoading}
              >
                {isLoading ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <>
                    Sign in
                    <ArrowRight className="h-4 w-4 ml-2" />
                  </>
                )}
              </Button>
            </form>
          </CardContent>
        </Card>

        {/* Footer */}
        <p className="text-center text-sm text-zinc-400 mt-6">
          Don't have an account?{" "}
          <Link
            href="/auth/register"
            className="text-indigo-400 hover:text-indigo-300 font-medium transition-colors"
          >
            Sign up
          </Link>
        </p>
      </div>
    </div>
  );
}