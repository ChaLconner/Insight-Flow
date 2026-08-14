import Image from "next/image";

export function SiteFooter() {
  return (
    <footer className="border-t border-white/10 py-12 bg-zinc-950">
      <div className="max-w-7xl mx-auto px-6 grid md:grid-cols-3 gap-8">
        <div className="col-span-2">
          <div className="flex items-center gap-2 font-bold text-xl tracking-tight mb-4">
            <Image
              src="/icon.svg"
              alt="Insight Flow Logo"
              width={24}
              height={24}
              className="w-6 h-6 rounded"
            />
            Insight Flow
          </div>
          <p className="text-muted-foreground max-w-sm">
            The all-in-one platform for modern engineering teams. Plan, track,
            and ship world-class software.
          </p>
        </div>
        <div className="md:text-right">
          <h4 className="font-semibold mb-4">Product</h4>
          <ul className="space-y-2 text-sm text-muted-foreground">
            <li>
              <a href="#features" className="hover:text-white">
                Features
              </a>
            </li>
            <li>
              <a href="#pricing" className="hover:text-white">
                Pricing
              </a>
            </li>
          </ul>
        </div>
      </div>
    </footer>
  );
}
