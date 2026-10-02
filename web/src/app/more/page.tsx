import { ChevronRight } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";

import { EXPLORE_NAV, PRIMARY_NAV, type NavItem } from "@/components/shell/nav-items";
import { PageHeader } from "@/components/shell/page-header";

export const metadata: Metadata = { title: "More" };

function Card({ item }: { item: NavItem }) {
  const Icon = item.icon;
  return (
    <li className="min-w-0">
      <Link
        href={item.href}
        className="group flex h-full min-h-[72px] items-center gap-4 rounded-xl border border-border bg-card p-4 shadow-e1 outline-none transition-colors hover:bg-surface-2 focus-visible:ring-2 focus-visible:ring-ring lg:min-h-[132px] lg:flex-col lg:items-start lg:p-5"
      >
        <span className="flex size-11 shrink-0 items-center justify-center rounded-lg bg-surface-2 text-muted-foreground group-hover:text-foreground lg:size-12">
          <Icon aria-hidden className="size-5 lg:size-6" strokeWidth={1.75} />
        </span>
        <span className="min-w-0 flex-1">
          <span className="font-display flex items-center gap-1 text-lg leading-6 font-semibold lg:text-xl">
            {item.label}
            <ChevronRight aria-hidden className="size-4 text-muted-foreground transition-transform group-hover:translate-x-0.5" />
          </span>
          {item.description && <span className="mt-0.5 block text-sm text-muted-foreground">{item.description}</span>}
        </span>
      </Link>
    </li>
  );
}

function Group({ id, title, items }: { id: string; title: string; items: NavItem[] }) {
  return (
    <section aria-labelledby={id} className="grid gap-3">
      <h2 id={id} className="text-overline text-muted-foreground">
        {title}
      </h2>
      <ul className="grid gap-3 sm:grid-cols-2 md:gap-4 lg:grid-cols-3 2xl:grid-cols-4">
        {items.map((item) => (
          <Card key={item.href} item={item} />
        ))}
      </ul>
    </section>
  );
}

export default function MorePage() {
  return (
    <>
      <PageHeader title="More" subtitle="Explore teams, players, venues, records and how accurate the model is." />
      <div className="grid gap-8">
        <Group id="more-explore" title="Explore" items={EXPLORE_NAV} />
        <Group id="more-main" title="Main sections" items={PRIMARY_NAV} />
      </div>
    </>
  );
}
