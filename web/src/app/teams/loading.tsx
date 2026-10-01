import { GridPageSkeleton } from "@/components/loaders/page-skeletons";

export default function Loading() {
  return <GridPageSkeleton label="Loading teams" count={10} />;
}
