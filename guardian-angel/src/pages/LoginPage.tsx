import { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Wifi, Eye, EyeOff, Loader2, ShieldCheck, ArrowLeft } from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "@/hooks/useAuth";
import { authApi } from "@/lib/api";

const LoginPage = () => {
  const navigate = useNavigate();
  const { login, verify2fa } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  // 2FA state
  const [needs2fa, setNeeds2fa] = useState(false);
  const [tempToken, setTempToken] = useState("");
  const [maskedEmail, setMaskedEmail] = useState("");
  const [countdown, setCountdown] = useState(60);
  const [otpDigits, setOtpDigits] = useState(["", "", "", "", "", ""]);
  const inputRefs = useRef<(HTMLInputElement | null)[]>([]);

  // Password reset state
  const [showForgotPassword, setShowForgotPassword] = useState(false);
  const [showResetPassword, setShowResetPassword] = useState(false);
  const [resetUsername, setResetUsername] = useState("");
  const [resetCode, setResetCode] = useState(["", "", "", "", "", ""]);
  const [resetCountdown, setResetCountdown] = useState(60);
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [resetMaskedEmail, setResetMaskedEmail] = useState("");
  const [isCodeVerified, setIsCodeVerified] = useState(false);
  const resetInputRefs = useRef<(HTMLInputElement | null)[]>([]);



  // Reset Countdown timer effect
  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (showForgotPassword && !isCodeVerified && resetMaskedEmail && resetCountdown > 0) {
      interval = setInterval(() => {
        setResetCountdown((prev) => {
          if (prev <= 1) {
            clearInterval(interval);
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [showForgotPassword, isCodeVerified, resetMaskedEmail, resetCountdown]);

  // 2FA Countdown timer effect
  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (needs2fa && countdown > 0) {
      interval = setInterval(() => {
        setCountdown((prev) => {
          if (prev <= 1) {
            clearInterval(interval);
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [needs2fa, countdown]);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!username || !password) {
      toast.error("Please enter username and password");
      return;
    }

    setIsLoading(true);

    try {
      const result = await login(username, password);

      if (result.requires2fa && result.tempToken) {
        setNeeds2fa(true);
        setTempToken(result.tempToken);
        setMaskedEmail(result.maskedEmail || "");
        setCountdown(60); // Reset countdown
        toast.info(result.maskedEmail
          ? `A verification code has been sent to ${result.maskedEmail}`
          : "A verification code has been sent");
      } else {
        toast.success("Welcome back!");
        navigate("/");
      }
    } catch (error: any) {
      toast.error(error.response?.data?.error || "Invalid credentials");
    } finally {
      setIsLoading(false);
    }
  };

  const handleOtpChange = (index: number, value: string) => {
    if (value.length > 1) value = value.slice(-1);
    if (value && !/^\d$/.test(value)) return;

    const newDigits = [...otpDigits];
    newDigits[index] = value;
    setOtpDigits(newDigits);

    if (value && index < 5) {
      inputRefs.current[index + 1]?.focus();
    }
  };

  const handleOtpKeyDown = (index: number, e: React.KeyboardEvent) => {
    if (e.key === "Backspace" && !otpDigits[index] && index > 0) {
      inputRefs.current[index - 1]?.focus();
    }
  };

  const handleOtpPaste = (e: React.ClipboardEvent) => {
    e.preventDefault();
    const pasted = e.clipboardData.getData("text").replace(/\D/g, "").slice(0, 6);
    const newDigits = [...otpDigits];
    for (let i = 0; i < 6; i++) {
      newDigits[i] = pasted[i] || "";
    }
    setOtpDigits(newDigits);
    const focusIdx = Math.min(pasted.length, 5);
    inputRefs.current[focusIdx]?.focus();
  };

  const handleVerify = async (e: React.FormEvent) => {
    e.preventDefault();
    const code = otpDigits.join("");

    if (code.length !== 6) {
      toast.error("Please enter the full 6-digit code");
      return;
    }

    setIsLoading(true);
    try {
      await verify2fa(code, tempToken);
      toast.success("Welcome back!");
      navigate("/");
    } catch (error: any) {
      toast.error(error.response?.data?.error || "Invalid verification code");
      setOtpDigits(["", "", "", "", "", ""]);
      inputRefs.current[0]?.focus();
    } finally {
      setIsLoading(false);
    }
  };

  const handleBack = () => {
    if (showResetPassword) {
      if (isCodeVerified) {
        // Go back to code verification step
        setIsCodeVerified(false);
        setNewPassword("");
        setConfirmPassword("");
      } else {
        // Go back to forgot password screen
        setShowResetPassword(false);
        setResetCode(["", "", "", "", "", ""]);
        setResetMaskedEmail("");
      }
    } else if (showForgotPassword) {
      // Go back to login screen
      setShowForgotPassword(false);
      setResetUsername("");
      setResetMaskedEmail("");
      setResetCountdown(60);
    } else {
      // Go back to login from 2FA
      setNeeds2fa(false);
      setTempToken("");
      setMaskedEmail("");
      setCountdown(60);
      setOtpDigits(["", "", "", "", "", ""]);
    }
  };

  const handleResetCodeChange = (index: number, value: string) => {
    if (value.length > 1) value = value.slice(-1);
    if (value && !/^\d$/.test(value)) return;

    const newDigits = [...resetCode];
    newDigits[index] = value;
    setResetCode(newDigits);

    if (value && index < 5) {
      resetInputRefs.current[index + 1]?.focus();
    }
  };

  const handleResetCodeKeyDown = (index: number, e: React.KeyboardEvent) => {
    if (e.key === "Backspace" && !resetCode[index] && index > 0) {
      resetInputRefs.current[index - 1]?.focus();
    }
  };

  const handleResetCodePaste = (e: React.ClipboardEvent) => {
    e.preventDefault();
    const pasted = e.clipboardData.getData("text").replace(/\D/g, "").slice(0, 6);
    const newDigits = [...resetCode];
    for (let i = 0; i < 6; i++) {
      newDigits[i] = pasted[i] || "";
    }
    setResetCode(newDigits);
    const focusIdx = Math.min(pasted.length, 5);
    resetInputRefs.current[focusIdx]?.focus();
  };

  const handleForgotPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      const result = await authApi.forgotPassword(resetUsername);
      setResetMaskedEmail(result.masked_email || "");
      setResetCountdown(60);
      setShowResetPassword(true);
      toast.info(result.masked_email
        ? `Reset code sent to ${result.masked_email}`
        : "If the username exists, a reset code has been sent");
    } catch (error: any) {
      toast.error(error.response?.data?.error || "Failed to send reset code");
    } finally {
      setIsLoading(false);
    }
  };

  const handleVerifyResetCode = async (e: React.FormEvent) => {
    e.preventDefault();
    const code = resetCode.join("");
    if (code.length !== 6) {
      toast.error("Please enter the complete reset code");
      return;
    }

    setIsLoading(true);
    try {
      await authApi.verifyResetCode(code);
      setIsCodeVerified(true);
      toast.success("Code verified! Please set your new password.");
    } catch (error: any) {
      toast.error(error.response?.data?.error || "Invalid or expired reset code");
      setResetCode(["", "", "", "", "", ""]);
      resetInputRefs.current[0]?.focus();
    } finally {
      setIsLoading(false);
    }
  };

  const handleResetPassword = async (e: React.FormEvent) => {
    e.preventDefault();

    if (newPassword !== confirmPassword) {
      toast.error("Passwords do not match");
      return;
    }

    if (newPassword.length < 8) {
      toast.error("Password must be at least 8 characters");
      return;
    }

    const code = resetCode.join("");
    setIsLoading(true);

    try {
      await authApi.resetPassword(code, newPassword);
      toast.success("Password reset successfully! You can now login.");
      setShowResetPassword(false);
      setShowForgotPassword(false);
      setResetUsername("");
      setResetCode(["", "", "", "", "", ""]);
      setNewPassword("");
      setConfirmPassword("");
      setResetMaskedEmail("");
      setIsCodeVerified(false);
    } catch (error: any) {
      toast.error(error.response?.data?.error || "Failed to reset password");
    } finally {
      setIsLoading(false);
    }
  };


  return (
    <div className="flex min-h-screen items-center justify-center bg-background network-grid p-4">
      {/* Background glow effects */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-primary/10 rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-primary/5 rounded-full blur-3xl" />
      </div>

      <div className="relative w-full max-w-md">
        {/* Logo */}
        <div className="mb-8 text-center">
          <div className="inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10 border border-primary/30 mb-4 animate-pulse-glow">
            {needs2fa ? <ShieldCheck className="h-8 w-8 text-primary" /> : <Wifi className="h-8 w-8 text-primary" />}
          </div>
          <h1 className="text-3xl font-bold text-foreground">HaresNet</h1>
          <p className="mt-2 text-muted-foreground">
            {needs2fa ? "Two-Factor Authentication" : "Network Management System"}
          </p>
        </div>

        {/* Login / 2FA / Forgot Password / Reset Card */}
        <div className="glass-card rounded-2xl border border-border p-8">
          {showResetPassword ? (
            !isCodeVerified ? (
              /* Step 1: Verify Code */
              <form onSubmit={handleVerifyResetCode} className="space-y-6">
                <div>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={handleBack}
                    className="mb-4 gap-2 text-muted-foreground"
                  >
                    <ArrowLeft className="h-4 w-4" />
                    Back
                  </Button>
                  <h2 className="text-xl font-semibold text-foreground">Verify Code</h2>
                  <p className="text-sm text-muted-foreground mt-1">
                    Enter the code sent to {resetMaskedEmail || "your email"}
                  </p>
                  <div className={`mt-2 text-sm font-medium ${resetCountdown <= 10 ? 'text-destructive' : 'text-primary'}`}>
                    ⏱ Expires in {resetCountdown}s
                  </div>
                </div>

                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label>Reset Code</Label>
                    <div className="flex justify-center gap-2" onPaste={handleResetCodePaste}>
                      {resetCode.map((digit, i) => (
                        <Input
                          key={i}
                          ref={(el) => { resetInputRefs.current[i] = el; }}
                          type="text"
                          inputMode="numeric"
                          maxLength={1}
                          value={digit}
                          onChange={(e) => handleResetCodeChange(i, e.target.value)}
                          onKeyDown={(e) => handleResetCodeKeyDown(i, e)}
                          className="w-12 h-14 text-center text-xl font-bold"
                          autoFocus={i === 0}
                        />
                      ))}
                    </div>
                  </div>
                </div>

                <Button
                  type="submit"
                  disabled={isLoading || resetCode.join("").length !== 6}
                  className="w-full h-12 text-base font-semibold"
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                      Verifying...
                    </>
                  ) : (
                    "Verify Code"
                  )}
                </Button>
              </form>
            ) : (
              /* Step 2: Set New Password */
              <form onSubmit={handleResetPassword} className="space-y-6">
                <div>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={handleBack}
                    className="mb-4 gap-2 text-muted-foreground"
                  >
                    <ArrowLeft className="h-4 w-4" />
                    Back
                  </Button>
                  <h2 className="text-xl font-semibold text-foreground">Set New Password</h2>
                  <p className="text-sm text-muted-foreground mt-1">
                    Create a strong password for your account
                  </p>
                </div>

                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="new-password">New Password</Label>
                    <Input
                      id="new-password"
                      type="password"
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      placeholder="Enter new password"
                      className="h-12"
                      autoFocus
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="confirm-password">Confirm Password</Label>
                    <Input
                      id="confirm-password"
                      type="password"
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      placeholder="Confirm new password"
                      className="h-12"
                    />
                  </div>
                </div>

                <Button
                  type="submit"
                  disabled={isLoading}
                  className="w-full h-12 text-base font-semibold"
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                      Resetting...
                    </>
                  ) : (
                    "Reset Password"
                  )}
                </Button>
              </form>
            )
          ) : showForgotPassword ? (
            <form onSubmit={handleForgotPassword} className="space-y-6">
              <div>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={handleBack}
                  className="mb-4 gap-2 text-muted-foreground"
                >
                  <ArrowLeft className="h-4 w-4" />
                  Back to login
                </Button>
                <h2 className="text-xl font-semibold text-foreground">Forgot Password</h2>
                <p className="text-sm text-muted-foreground mt-1">
                  Enter your username to receive a password reset code
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="reset-username">Username</Label>
                <Input
                  id="reset-username"
                  type="text"
                  value={resetUsername}
                  onChange={(e) => setResetUsername(e.target.value)}
                  placeholder="Enter your username"
                  className="h-12"
                  autoFocus
                />
              </div>

              <Button
                type="submit"
                disabled={isLoading || !resetUsername}
                className="w-full h-12 text-base font-semibold"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                    Sending code...
                  </>
                ) : (
                  "Send Reset Code"
                )}
              </Button>
            </form>
          ) : !needs2fa ? (
            <form onSubmit={handleLogin} className="space-y-6">
              <div className="space-y-2">
                <Label htmlFor="username">Username</Label>
                <Input
                  id="username"
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="Enter your username"
                  className="h-12"
                  autoComplete="username"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="password">Password</Label>
                <div className="relative">
                  <Input
                    id="password"
                    type={showPassword ? "text" : "password"}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Enter your password"
                    className="h-12 pr-12"
                    autoComplete="current-password"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-4 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                  >
                    {showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                  </button>
                </div>
              </div>

              <div className="flex justify-end">
                <button
                  type="button"
                  onClick={() => setShowForgotPassword(true)}
                  className="text-sm text-primary hover:underline"
                >
                  Forgot password?
                </button>
              </div>

              <Button
                type="submit"
                disabled={isLoading}
                className="w-full h-12 text-base font-semibold"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                    Signing in...
                  </>
                ) : (
                  "Sign In"
                )}
              </Button>
            </form>
          ) : (
            <form onSubmit={handleVerify} className="space-y-6">
              <div className="text-center space-y-3">
                <p className="text-sm text-muted-foreground">
                  A 6-digit verification code has been sent to
                </p>
                <p className="text-base font-semibold text-foreground">
                  {maskedEmail || "your email"}
                </p>
                <div className="flex items-center justify-center gap-2">
                  <div className={`text-lg font-bold tabular-nums ${countdown <= 10 ? 'text-destructive' : 'text-primary'}`}>
                    {Math.floor(countdown / 60)}:{(countdown % 60).toString().padStart(2, '0')}s
                  </div>
                  <span className="text-xs text-muted-foreground">remaining</span>
                </div>
              </div>

              <div className="flex justify-center gap-2" onPaste={handleOtpPaste}>
                {otpDigits.map((digit, i) => (
                  <Input
                    key={i}
                    ref={(el) => { inputRefs.current[i] = el; }}
                    type="text"
                    inputMode="numeric"
                    maxLength={1}
                    value={digit}
                    onChange={(e) => handleOtpChange(i, e.target.value)}
                    onKeyDown={(e) => handleOtpKeyDown(i, e)}
                    className="w-12 h-14 text-center text-xl font-bold"
                    autoFocus={i === 0}
                  />
                ))}
              </div>

              <Button
                type="submit"
                disabled={isLoading || otpDigits.join("").length !== 6}
                className="w-full h-12 text-base font-semibold"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                    Verifying...
                  </>
                ) : (
                  <>
                    <ShieldCheck className="mr-2 h-5 w-5" />
                    Verify & Sign In
                  </>
                )}
              </Button>

              <Button
                type="button"
                variant="ghost"
                onClick={handleBack}
                className="w-full gap-2 text-muted-foreground"
              >
                <ArrowLeft className="h-4 w-4" />
                Back to login
              </Button>
            </form>
          )}
        </div>

        {/* Footer */}
        <p className="mt-6 text-center text-sm text-muted-foreground">
          Secure network management for your home
        </p>
      </div>
    </div >
  );
};

export default LoginPage;

