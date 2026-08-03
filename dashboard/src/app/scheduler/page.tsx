import DataPage from "@/components/shared/DataPage";

export default function SchedulerPage() {
  return <DataPage title="Scheduler" endpoint="/api/scheduler" refreshMs={5000} />;
}
