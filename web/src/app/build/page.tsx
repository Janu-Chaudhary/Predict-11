import type { Metadata } from "next";

import { BuilderDemo } from "@/components/builder/builder-demo";
import { PageHeader } from "@/components/shell/page-header";
import { SampleDataNote } from "@/components/shell/sample-data-note";

export const metadata: Metadata = { title: "Build" };

export default function BuildPage() {
  return (
    <>
      <PageHeader
        overline="Fantasy builder"
        title="Build your XI"
        subtitle="Pitch view with lock / exclude. The optimiser, risk slider and multi-lineup portfolio land later."
      />
      <SampleDataNote className="mb-4">The XI below is placeholder data, not a prediction. “Re-optimise” is simulated to preview the inline loader.</SampleDataNote>
      <BuilderDemo />
    </>
  );
}
