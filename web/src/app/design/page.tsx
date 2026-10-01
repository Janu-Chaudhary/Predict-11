import type { Metadata } from "next";

import { PageHeader } from "@/components/shell/page-header";
import { SampleDataNote } from "@/components/shell/sample-data-note";

import { Gallery } from "./gallery";

export const metadata: Metadata = { title: "Design system", robots: { index: false } };

/** Living reference of the Floodlight shared components (not in the nav). */
export default function DesignPage() {
  return (
    <>
      <PageHeader overline="Floodlight" title="Design system" subtitle="Shared components with sample props: the grammar every page reuses." />
      <SampleDataNote className="mb-6">Everything on this page is invented to exercise the components.</SampleDataNote>
      <Gallery />
    </>
  );
}
