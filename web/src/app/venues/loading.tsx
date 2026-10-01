import { HeaderSkeleton } from "@/components/loaders/page-skeletons";
import { VenueListSkeleton } from "@/features/venues/venue-list";

export default function Loading() {
  return (
    <>
      <HeaderSkeleton />
      <VenueListSkeleton />
    </>
  );
}
