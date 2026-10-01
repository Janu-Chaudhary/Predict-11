import { cn } from "@/lib/utils"

/**
 * Floodlight-sweep skeleton block (§7.2 #3): surface-2 with a 6% light band passing
 * diagonally every 1.6 s. Static under prefers-reduced-motion.
 */
function Skeleton({ className, ...props }: React.ComponentProps<"div">) {
  return <div data-slot="skeleton" aria-hidden className={cn("sk", className)} {...props} />
}

export { Skeleton }
