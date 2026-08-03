import DataPage from "@/components/shared/DataPage";

export default function CouncilPage() {
  return <DataPage title="Council" endpoint="/api/council" refreshMs={5000} />;
}
