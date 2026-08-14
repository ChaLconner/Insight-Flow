import type { Metadata } from "next";
import { LegalPage, type LegalSection } from "@/components/legal/LegalPage";

export const metadata: Metadata = {
  title: "Privacy Policy",
  description: "How Insight Flow handles information used by the service.",
};

const sections: LegalSection[] = [
  {
    title: "Information we handle",
    paragraphs: [
      "Insight Flow may handle information needed to provide the service, such as account and contact details, workspace members, projects, tasks, comments, and files or links that users choose to store. We also receive technical and usage information needed to keep the service secure and reliable.",
    ],
  },
  {
    title: "How information is used",
    paragraphs: [
      "We use this information to authenticate users, provide collaboration features, respond to support requests, improve reliability, and detect or prevent fraud, abuse, and security incidents.",
    ],
  },
  {
    title: "Access and sharing",
    paragraphs: [
      "Workspace content is available to the users and organizations that have been granted access. We may also use service providers that support hosting, storage, monitoring, authentication, or communications, subject to appropriate access and security controls.",
    ],
  },
  {
    title: "Security and retention",
    paragraphs: [
      "We use reasonable technical and organizational safeguards for information handled by the service. Information is retained for as long as needed to provide the service, meet legal obligations, resolve disputes, and enforce agreements, unless your organization controls the retention period for its workspace.",
    ],
  },
  {
    title: "Your choices",
    paragraphs: [
      "You can review or update account information through the service when those controls are available. For requests about workspace data, contact your workspace administrator or the Insight Flow support team.",
    ],
  },
];

export default function PrivacyPage() {
  return (
    <LegalPage
      title="Privacy Policy"
      intro="An overview of the information Insight Flow handles to provide a secure collaboration service."
      updatedAt="August 14, 2026"
      sections={sections}
    />
  );
}
