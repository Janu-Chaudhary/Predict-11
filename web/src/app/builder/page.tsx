import type { Metadata } from "next";

import { BuilderDemo } from "@/components/builder/builder-demo";
import { PageHeader } from "@/components/shell/page-header";

export const metadata: Metadata = { title: "Builder" };

export default function BuilderPage() {
  return (
    <>
      <PageHeader
        title="Team builder"
        subtitle="Pitch view with lock / exclude. Mock data — the optimizer, risk slider and multi-lineup portfolio land later."
      />
      <BuilderDemo />
    </>
  );
}
