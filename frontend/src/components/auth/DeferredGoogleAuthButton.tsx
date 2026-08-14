"use client";

import dynamic from "next/dynamic";
import { Button } from "@/components/ui/button";
import { GoogleIcon } from "@/components/auth/GoogleIcon";
import type { GoogleAuthButtonProps } from "@/components/auth/GoogleAuthButton";
import { useState } from "react";

const GoogleAuthButton = dynamic<GoogleAuthButtonProps>(
  () =>
    import("@/components/auth/GoogleAuthButton").then(
      (module) => module.GoogleAuthButton,
    ),
  {
    ssr: false,
    loading: () => (
      <Button
        variant="outline"
        className="w-full bg-slate-900 border-slate-700 text-white"
        disabled
      >
        <GoogleIcon />
        Continue with Google
      </Button>
    ),
  },
);

export function DeferredGoogleAuthButton(
  props: Readonly<GoogleAuthButtonProps>,
) {
  const [shouldLoad, setShouldLoad] = useState(false);
  const [startImmediately, setStartImmediately] = useState(false);
  const hasClientId = Boolean(process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID);

  if (shouldLoad) {
    return <GoogleAuthButton {...props} autoStart={startImmediately} />;
  }

  const loadOnIntent = (startImmediately = false) => {
    if (hasClientId && !props.disabled) {
      setShouldLoad(true);
      if (startImmediately) {
        setStartImmediately(true);
      }
    }
  };

  return (
    <Button
      variant="outline"
      className="w-full bg-slate-900 hover:bg-slate-800 border-slate-700 text-white transition-all hover:scale-[1.02]"
      onClick={() => loadOnIntent(true)}
      onFocus={() => loadOnIntent()}
      onPointerDown={() => loadOnIntent()}
      onPointerEnter={() => loadOnIntent()}
      disabled={props.disabled}
      title={props.title}
    >
      <GoogleIcon />
      {props.label}
    </Button>
  );
}
