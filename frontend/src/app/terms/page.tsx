import type { Metadata } from "next";
import { LegalPage, type LegalSection } from "@/components/legal/LegalPage";

export const metadata: Metadata = {
  title: "Terms of Service",
  description: "Terms governing the use of Insight Flow.",
};

const sections: LegalSection[] = [
  {
    title: "Using Insight Flow",
    paragraphs: [
      "Insight Flow provides project, task, and team collaboration tools. By creating an account or using the service, you agree to use it only for lawful business or personal work and to follow these terms.",
    ],
  },
  {
    title: "Accounts and workspace content",
    paragraphs: [
      "You are responsible for keeping your sign-in information secure and for the activity carried out through your account. You are also responsible for ensuring that your workspace content is accurate, lawful, and shared only with people who should have access to it.",
    ],
  },
  {
    title: "Acceptable use",
    paragraphs: [
      "Do not misuse the service or interfere with its operation. In particular, do not attempt to gain unauthorized access, upload malicious code, abuse automated requests, or use Insight Flow to violate another person's rights or applicable law.",
    ],
  },
  {
    title: "Availability and changes",
    paragraphs: [
      "We may improve, change, or temporarily suspend parts of the service to maintain security and reliability. We will make reasonable efforts to communicate material changes to these terms or to the service when appropriate.",
    ],
  },
  {
    title: "Questions",
    paragraphs: [
      "If you have a question about these terms or need help with your account, contact the Insight Flow support team through the support channel provided by your organization.",
    ],
  },
];

export default function TermsPage() {
  return (
    <LegalPage
      title="Terms of Service"
      intro="The rules for using Insight Flow and collaborating in a workspace."
      updatedAt="August 14, 2026"
      sections={sections}
    />
  );
}
