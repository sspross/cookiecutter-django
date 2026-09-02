/**
 * Dashboard — / route.
 *
 * Inline cards, no abstractions. Duplicate the API Keys card for your first
 * domain model; extract a <StatCard> only once a third card lands.
 */
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useApiKeys } from "@/queries/use-api-keys";

export function DashboardRoute() {
  const { data, isLoading } = useApiKeys();
  const activeCount = data?.filter((k) => !k.revoked_at).length ?? 0;

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      <Card>
        <CardHeader>
          <CardDescription>API Keys</CardDescription>
          <CardTitle className="text-3xl">
            {isLoading ? <Skeleton className="h-9 w-12" /> : activeCount}
          </CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          Active keys for headless API access.
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardDescription>Recent Activity</CardDescription>
          <CardTitle className="text-base font-normal text-muted-foreground">
            No recent activity yet.
          </CardTitle>
        </CardHeader>
      </Card>
    </div>
  );
}
