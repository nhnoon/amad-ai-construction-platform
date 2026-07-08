import { useState } from "react";
import { useAuth } from "../context/AuthContext";
import { useLocation } from "wouter";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { LogoMark } from "../components/LogoMark";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const [, setLocation] = useLocation();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login({ email, password });
      setLocation("/");
    } catch {
      setError("Invalid email or password. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex bg-background">
      {/* Left panel — brand */}
      <div className="hidden lg:flex lg:w-1/2 xl:w-[55%] flex-col justify-between bg-sidebar p-12">
        <div>
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-2xl bg-sidebar-primary flex items-center justify-center shadow-inner shrink-0">
              <LogoMark className="w-7 h-7 text-sidebar-primary-foreground" />
            </div>
            <div>
              <p className="text-sidebar-foreground font-bold text-2xl tracking-wide leading-tight">
                Amad
              </p>
              <p className="text-sidebar-foreground/50 text-xs uppercase tracking-widest">
                Construction Intelligence
              </p>
            </div>
          </div>

          <div className="mt-16 max-w-sm">
            <h1 className="text-4xl font-bold text-sidebar-foreground leading-tight">
              Operational intelligence for the built world.
            </h1>
            <p className="mt-4 text-sidebar-foreground/60 text-lg leading-relaxed">
              Real-time visibility across projects, procurement, safety, and
              quality — purpose-built for the Saudi construction market.
            </p>
          </div>
        </div>

        <div>
          <p className="text-sidebar-foreground/40 text-xs uppercase tracking-widest">
            Trusted for Saudi construction
          </p>
        </div>
      </div>

      {/* Right panel — form */}
      <div className="flex-1 flex flex-col items-center justify-center px-6 py-12 sm:px-12">
        {/* Mobile logo */}
        <div className="lg:hidden flex items-center gap-3 mb-10">
          <div className="w-10 h-10 rounded-xl bg-primary flex items-center justify-center shrink-0">
            <LogoMark className="w-6 h-6 text-primary-foreground" />
          </div>
          <div>
            <p className="font-bold text-foreground text-lg leading-tight">Amad</p>
            <p className="text-muted-foreground text-xs uppercase tracking-widest">
              Construction Intelligence
            </p>
          </div>
        </div>

        <div className="w-full max-w-sm">
          <div className="mb-8">
            <h2 className="text-2xl font-bold text-foreground">Sign in</h2>
            <p className="text-muted-foreground text-sm mt-1">
              Enter your credentials to access the platform
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="space-y-1.5">
              <Label htmlFor="email" className="text-sm font-medium">
                Email address
              </Label>
              <Input
                id="email"
                type="email"
                autoComplete="email"
                placeholder="you@company.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="h-11"
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="password" className="text-sm font-medium">
                Password
              </Label>
              <Input
                id="password"
                type="password"
                autoComplete="current-password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="h-11"
              />
            </div>

            {error && (
              <p className="text-sm text-destructive bg-destructive/10 rounded-lg px-3 py-2">
                {error}
              </p>
            )}

            <Button
              type="submit"
              className="w-full h-11 font-semibold"
              disabled={loading}
            >
              {loading ? (
                <span className="flex items-center gap-2">
                  <span className="w-4 h-4 rounded-full border-2 border-primary-foreground border-t-transparent animate-spin" />
                  Signing in…
                </span>
              ) : (
                "Sign in"
              )}
            </Button>
          </form>

          <p className="mt-8 text-center text-xs text-muted-foreground">
            Amad Construction Intelligence © {new Date().getFullYear()}
          </p>
        </div>
      </div>
    </div>
  );
}
