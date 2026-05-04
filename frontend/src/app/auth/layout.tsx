import { AuthShell } from "@/components/auth/AuthShell";

/**
 * Inline script that runs BEFORE React hydrates.
 *
 * When the user clicks "Continue with GitHub", we set a sessionStorage flag
 * (`auth_oauth_started`). If the user then presses the browser Back button,
 * the auth page loads again. This script detects the flag and forces a hard
 * reload so that React, the canvas animation, and the Google SDK all
 * initialise from a clean slate. The flag is removed first so the reloaded
 * page won't loop.
 *
 * We also clear any stale `document.body.style.overflow = "hidden"` that a
 * Dialog component may have left behind, which would block all interaction.
 */
const BFCACHE_GUARD_SCRIPT = `
(function(){
  try{
    if(sessionStorage.getItem("auth_oauth_started")==="1"){
      sessionStorage.removeItem("auth_oauth_started");
      setTimeout(function(){location.reload();},0);
    }
    if(document.body)document.body.style.overflow="";
  }catch(e){}
})();
`;

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <>
      {/* Pre-React guard: runs outside React lifecycle */}
      <script dangerouslySetInnerHTML={{ __html: BFCACHE_GUARD_SCRIPT }} />
      <AuthShell>{children}</AuthShell>
    </>
  );
}
