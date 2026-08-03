import DataPage from "@/components/shared/DataPage";

export default function DebatePage() {
  return <DataPage title="Debate" endpoint="/api/debate" refreshMs={5000} />;
}
