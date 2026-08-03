import DataPage from "@/components/shared/DataPage";

export default function EcosystemPage() {
  return <DataPage title="Ecosystem" endpoint="/api/overview" refreshMs={15000} />;
}
