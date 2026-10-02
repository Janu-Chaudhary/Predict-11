"use client";

import { Search } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { Input } from "@/components/ui/input";

import { GLOSSARY, GLOSSARY_BY_ID, type GlossaryEntry } from "./glossary";
import { Chip, Term } from "./ui";

const CATEGORIES = [...new Set(GLOSSARY.map((g) => g.category))];

export function searchGlossary(q: string, cat: GlossaryEntry["category"] | null): GlossaryEntry[] {
  const needle = q.trim().toLowerCase();
  return GLOSSARY.filter((g) => (!cat || g.category === cat) && (!needle || `${g.term} ${g.short} ${g.body}`.toLowerCase().includes(needle)));
}

export function GlossaryTab() {
  const [q, setQ] = useState("");
  const [cat, setCat] = useState<GlossaryEntry["category"] | null>(null);
  const entries = useMemo(() => searchGlossary(q, cat), [q, cat]);

  // Arriving via a <Term> link: scroll the anchored entry into view once it is rendered.
  useEffect(() => {
    const id = window.location.hash.slice(1);
    if (id) document.getElementById(id)?.scrollIntoView({ block: "start" });
  }, []);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative w-full sm:w-80">
          <Search aria-hidden className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search terms" aria-label="Search the glossary" className="h-9 rounded-[10px] bg-card pl-9" />
        </div>
        <span className="num text-xs text-muted-foreground">{entries.length} terms</span>
      </div>
      <div className="no-scrollbar -mx-4 flex gap-1.5 overflow-x-auto px-4 md:mx-0 md:flex-wrap md:px-0" role="group" aria-label="Filter by category">
        <Chip active={cat === null} onClick={() => setCat(null)}>
          All
        </Chip>
        {CATEGORIES.map((c) => (
          <Chip key={c} active={cat === c} onClick={() => setCat(cat === c ? null : c)}>
            {c}
          </Chip>
        ))}
      </div>
      <dl className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        {entries.map((g) => (
          <div
            key={g.id}
            id={`term-${g.id}`}
            className="scroll-mt-24 rounded-xl border border-border bg-card p-4 shadow-e1 target:border-brand target:ring-2 target:ring-brand/40"
          >
            <p className="text-overline text-muted-foreground">{g.category}</p>
            <dt className="mt-1 text-base font-semibold">{g.term}</dt>
            <dd className="mt-1 space-y-2 text-sm leading-relaxed">
              <p className="font-medium text-foreground">{g.short}</p>
              <p className="text-foreground/85">{g.body}</p>
              {g.formula && <code className="block overflow-x-auto rounded-md bg-surface-2 px-3 py-2 font-mono text-[13px] whitespace-pre">{g.formula}</code>}
              {g.here && (
                <p className="rounded-md border-l-2 border-brand bg-surface-2/60 px-3 py-1.5 text-[13px]">
                  <span className="font-semibold">In this model: </span>
                  {g.here}
                </p>
              )}
              {g.related && g.related.length > 0 && (
                <p className="text-xs text-muted-foreground">
                  Related:{" "}
                  {g.related
                    .filter((r) => GLOSSARY_BY_ID[r])
                    .map((r, i) => (
                      <span key={r}>
                        {i > 0 && ", "}
                        <Term id={r}>{GLOSSARY_BY_ID[r].term}</Term>
                      </span>
                    ))}
                </p>
              )}
            </dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
