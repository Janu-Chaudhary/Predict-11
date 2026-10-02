"use client";

import { Search } from "lucide-react";
import { useMemo, useState } from "react";

import { StatTable, type StatColumn } from "@/components/data/stat-table";
import { Input } from "@/components/ui/input";

import { HBars, Heatmap } from "./charts";
import { fmtNum, fmtPct, fmtValue } from "./format";
import { correlationInsight, importanceInsight } from "./insights";
import type { FeatureInfo, Telemetry } from "./types";
import { Chip, Grid, LabCard, LearnMore, Segmented, Term } from "./ui";

type ImpKey = "gain" | "split" | "shap";

const IMP_LABEL: Record<ImpKey, string> = { gain: "Gain", split: "Split count", shap: "Mean |SHAP|" };

export function shares(features: FeatureInfo[], key: ImpKey): Map<string, number> {
  const tot = features.reduce((s, f) => s + (f[key] ?? 0), 0) || 1;
  return new Map(features.map((f) => [f.name, (f[key] ?? 0) / tot]));
}

export function filterFeatures(features: FeatureInfo[], q: string, groups: Set<string>): FeatureInfo[] {
  const needle = q.trim().toLowerCase();
  return features.filter((f) => (groups.size === 0 || groups.has(f.group)) && (!needle || f.name.toLowerCase().includes(needle) || f.description.toLowerCase().includes(needle)));
}

export function FeaturesTab({ t }: { t: Telemetry }) {
  const [q, setQ] = useState("");
  const [groups, setGroups] = useState<Set<string>>(new Set());
  const [imp, setImp] = useState<ImpKey>("gain");
  const [topN, setTopN] = useState<"20" | "all">("20");
  const allGroups = useMemo(() => [...new Set(t.features.map((f) => f.group))], [t.features]);
  const gainShare = useMemo(() => shares(t.features, "gain"), [t.features]);
  const rows = useMemo(() => filterFeatures(t.features, q, groups), [t.features, q, groups]);
  const hasShap = t.features.some((f) => f.shap !== null);

  const ranked = useMemo(() => {
    const sh = shares(t.features, imp);
    return [...t.features]
      .sort((a, b) => (b[imp] ?? 0) - (a[imp] ?? 0))
      .slice(0, topN === "20" ? 20 : undefined)
      .map((f) => ({ key: f.name, label: <span className="font-mono text-xs">{f.name}</span>, value: imp === "shap" ? (f.shap ?? 0) : sh.get(f.name) ?? 0, title: f.description }));
  }, [t.features, imp, topN]);

  const byGroup = useMemo(() => {
    const m = new Map<string, number>();
    for (const f of t.features) m.set(f.group, (m.get(f.group) ?? 0) + (gainShare.get(f.name) ?? 0));
    return [...m.entries()].sort((a, b) => b[1] - a[1]).map(([g, v]) => ({ key: g, label: g, value: v, sub: `${t.features.filter((f) => f.group === g).length}` }));
  }, [t.features, gainShare]);

  const toggleGroup = (g: string) =>
    setGroups((prev) => {
      const next = new Set(prev);
      if (next.has(g)) next.delete(g);
      else next.add(g);
      return next;
    });

  const columns: StatColumn<FeatureInfo>[] = [
    {
      key: "name",
      header: "Feature",
      align: "left",
      sortable: true,
      sticky: true,
      value: (f) => f.name,
      cell: (f) => (
        <div className="max-w-[22rem] min-w-[12rem] py-1.5">
          <div className="font-mono text-[13px] font-medium">{f.name}</div>
          <div className="text-xs leading-snug whitespace-normal text-muted-foreground">{f.description}</div>
        </div>
      ),
      className: "bg-card",
    },
    { key: "group", header: "Group", align: "left", sortable: true, value: (f) => f.group, cell: (f) => <span className="text-xs">{f.group}</span>, hideBelow: "md" },
    { key: "gain", header: "Gain %", sortable: true, value: (f) => gainShare.get(f.name) ?? 0, cell: (f) => fmtPct(gainShare.get(f.name) ?? 0, 1) },
    { key: "split", header: "Splits", sortable: true, value: (f) => f.split, cell: (f) => fmtNum(f.split, 0), hideBelow: "sm" },
    ...(hasShap ? [{ key: "shap", header: "|SHAP|", sortable: true, value: (f: FeatureInfo) => f.shap, cell: (f: FeatureInfo) => fmtNum(f.shap, 2) } satisfies StatColumn<FeatureInfo>] : []),
    { key: "missing", header: "Missing", sortable: true, value: (f) => f.missingRate, cell: (f) => fmtPct(f.missingRate, 1) },
    { key: "mean", header: "Mean", sortable: true, value: (f) => f.mean, cell: (f) => fmtValue(f.mean), hideBelow: "md" },
    { key: "std", header: "SD", sortable: true, value: (f) => f.std, cell: (f) => fmtValue(f.std), hideBelow: "lg" },
    { key: "min", header: "Min", sortable: true, value: (f) => f.min, cell: (f) => fmtValue(f.min), hideBelow: "lg" },
    { key: "max", header: "Max", sortable: true, value: (f) => f.max, cell: (f) => fmtValue(f.max), hideBelow: "lg" },
  ];

  return (
    <div className="space-y-6">
      <section className="space-y-3">
        <div className="flex flex-wrap items-center gap-2">
          <div className="relative w-full sm:w-72">
            <Search aria-hidden className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search features or descriptions" aria-label="Search features" className="h-9 rounded-[10px] bg-card pl-9" />
          </div>
          <span className="num text-xs text-muted-foreground">
            {rows.length} of {t.features.length} features
          </span>
        </div>
        <div className="no-scrollbar -mx-4 flex gap-1.5 overflow-x-auto px-4 md:mx-0 md:flex-wrap md:px-0" role="group" aria-label="Filter by group">
          <Chip active={groups.size === 0} onClick={() => setGroups(new Set())}>
            All groups
          </Chip>
          {allGroups.map((g) => (
            <Chip key={g} active={groups.has(g)} onClick={() => toggleGroup(g)}>
              {g}
            </Chip>
          ))}
        </div>
        <StatTable columns={columns} rows={rows} rowKey={(f) => f.name} caption="All model features with statistics and importance" initialSort={{ key: "gain", dir: "desc" }} dense maxHeight="min(70dvh, 40rem)" />
        <LearnMore
          learn={{
            concept: (
              <>
                A feature is one input number the model sees for a player-match. <Term id="feature-importance">Gain</Term> = how much the splits on a feature reduced the loss in total (shown as a
                share of all gain); splits = how often it was used; <Term id="shap">mean |SHAP|</Term> = its average effect on a prediction, in points. Missing = share of rows with no value
                (e.g. a debutant has no form); LightGBM learns which way to send missing values at each split.
              </>
            ),
            read: "Sort any column. Click a group chip to filter; search matches names and descriptions.",
            good: "Importance concentrated in a few sensible features (recent form, role, batting position) is expected; a high-importance feature that makes no cricket sense is a red flag for leakage.",
            ours: importanceInsight(t.features, "gain"),
          }}
        />
      </section>

      <Grid cols={2}>
        <LabCard
          title="Feature importance"
          caption={`Top features by ${IMP_LABEL[imp].toLowerCase()} on the mean head. Toggle the measure to see how the ranking shifts.`}
          actions={
            <>
              <Segmented size="sm" label="Importance measure" value={imp} onChange={setImp} options={(["gain", "split", ...(hasShap ? ["shap" as const] : [])] as ImpKey[]).map((k) => ({ key: k, label: IMP_LABEL[k] }))} />
              <Segmented size="sm" label="How many" value={topN} onChange={setTopN} options={[{ key: "20", label: "Top 20" }, { key: "all", label: "All" }]} />
            </>
          }
          table={{ columns: ["Feature", IMP_LABEL[imp]], rows: ranked.map((r) => [r.key, imp === "shap" ? fmtNum(r.value, 3) : fmtPct(r.value, 2)]) }}
          learn={{
            concept: "Gain and split come from the trees' structure; SHAP measures effect on predictions. They usually agree on the top features but can disagree lower down: a feature used in many small splits ranks high on split count yet low on gain.",
            read: "Longer bar = more important. Gain and split bars are shares of the total; SHAP bars are average points of impact per prediction.",
            good: "Gain and SHAP rankings broadly agree; the top features make cricket sense.",
            ours: importanceInsight(t.features, imp),
          }}
        >
          <HBars items={ranked} fmt={(n) => (imp === "shap" ? fmtNum(n, 2) : fmtPct(n, 1))} />
        </LabCard>

        <LabCard
          title="Importance by feature group"
          caption="Share of total gain earned by each group of related features (number of features in grey)."
          table={{ columns: ["Group", "Gain share"], rows: byGroup.map((g) => [g.key, fmtPct(g.value, 1)]) }}
          learn={{
            concept: "Grouping shows which kind of information the model relies on: form, craft, matchups, context or conditions.",
            read: "Bar = summed gain share of the group's features.",
            good: "Form dominating is normal for fantasy points; conditions and matchups add smaller, real gains.",
            ours: byGroup.length ? `${byGroup[0].label} carries ${fmtPct(byGroup[0].value)} of all gain; ${byGroup.at(-1)!.label} the least (${fmtPct(byGroup.at(-1)!.value, 1)}).` : undefined,
          }}
        >
          <HBars items={byGroup} fmt={(n) => fmtPct(n, 1)} />
        </LabCard>
      </Grid>

      {t.correlations && (
        <LabCard
          title={`Correlation between the top ${t.correlations.features.length} features`}
          caption="Pearson correlation for each pair of the most important features: violet = rise together, gold = move oppositely."
          table={{ columns: ["Feature", ...t.correlations.features], rows: t.correlations.matrix.map((row, i) => [t.correlations!.features[i], ...row.map((r) => fmtNum(r, 2))]) }}
          learn={{
            concept: (
              <>
                <Term id="correlation">Correlated</Term> features carry overlapping information (e.g. mean of last 5 and last 10 games). Trees pick one of them almost arbitrarily at each split, so
                importance gets shared and a single feature can look less important than the information it carries.
              </>
            ),
            formula: "r = cov(x, y) / (σx · σy)",
            read: "Each cell is one pair; the diagonal is always 1. Hover a cell for the exact value.",
            good: "Blocks of high correlation within a group (form windows) are expected. They don't hurt tree models much, but they make importance harder to read.",
            ours: correlationInsight(t.correlations.features, t.correlations.matrix),
          }}
        >
          <Heatmap features={t.correlations.features} matrix={t.correlations.matrix} />
        </LabCard>
      )}
    </div>
  );
}
