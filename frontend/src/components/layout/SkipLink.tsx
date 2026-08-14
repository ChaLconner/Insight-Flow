"use client";

export function SkipLink() {
  const handleClick = (event: React.MouseEvent<HTMLAnchorElement>) => {
    const target = document.getElementById("main-content");
    if (!target) {
      return;
    }

    event.preventDefault();
    target.focus({ preventScroll: true });
    target.scrollIntoView({ block: "start" });
    window.history.replaceState(null, "", "#main-content");
  };

  return (
    <a
      href="#main-content"
      onClick={handleClick}
      className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:p-4 focus:bg-background focus:text-foreground focus:top-0 focus:left-0 transition-all"
    >
      Skip to content
    </a>
  );
}
