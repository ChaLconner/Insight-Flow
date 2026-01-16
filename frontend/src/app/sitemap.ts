import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Insight Flow",
  description: "Modern project management platform with glassmorphism design",
};

export default function Sitemap() {
  return [
    {
      url: `${process.env.NEXT_PUBLIC_APP_URL}/`,
      lastModified: new Date(),
    },
    {
      url: `${process.env.NEXT_PUBLIC_APP_URL}/auth/login`,
      lastModified: new Date(),
    },
    {
      url: `${process.env.NEXT_PUBLIC_APP_URL}/auth/register`,
      lastModified: new Date(),
    },
    {
      url: `${process.env.NEXT_PUBLIC_APP_URL}/pricing`,
      lastModified: new Date(),
    },
    {
      url: `${process.env.NEXT_PUBLIC_APP_URL}/features`,
      lastModified: new Date(),
    },
  ];
}
