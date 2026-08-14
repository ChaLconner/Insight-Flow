import Link from "next/link";
import { ArrowLeft } from "lucide-react";

export interface LegalSection {
  title: string;
  paragraphs: string[];
  bullets?: string[];
}

interface LegalPageProps {
  title: string;
  intro: string;
  updatedAt: string;
  sections: LegalSection[];
}

export function LegalPage({
  title,
  intro,
  updatedAt,
  sections,
}: Readonly<LegalPageProps>) {
  return (
    <main
      id="main-content"
      tabIndex={-1}
      className="min-h-screen bg-background px-4 py-10 text-foreground sm:px-6 lg:px-8"
    >
      <div className="mx-auto max-w-4xl">
        <Link
          href="/"
          className="inline-flex items-center gap-2 text-sm text-muted-foreground transition-colors hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4" aria-hidden="true" />
          Back to home
        </Link>

        <header className="mt-10 border-b border-border pb-8">
          <p className="text-sm font-medium uppercase tracking-[0.2em] text-primary">
            Insight Flow
          </p>
          <h1 className="mt-3 text-4xl font-bold tracking-tight sm:text-5xl">
            {title}
          </h1>
          <p className="mt-4 max-w-3xl text-lg text-muted-foreground">{intro}</p>
          <p className="mt-4 text-sm text-muted-foreground">
            Last updated: {updatedAt}
          </p>
        </header>

        <article className="space-y-10 py-10">
          {sections.map((section) => (
            <section key={section.title}>
              <h2 className="text-2xl font-semibold tracking-tight">
                {section.title}
              </h2>
              <div className="mt-3 space-y-3 text-muted-foreground leading-7">
                {section.paragraphs.map((paragraph) => (
                  <p key={paragraph}>{paragraph}</p>
                ))}
                {section.bullets ? (
                  <ul className="list-disc space-y-2 pl-6">
                    {section.bullets.map((bullet) => (
                      <li key={bullet}>{bullet}</li>
                    ))}
                  </ul>
                ) : null}
              </div>
            </section>
          ))}
        </article>
      </div>
    </main>
  );
}
