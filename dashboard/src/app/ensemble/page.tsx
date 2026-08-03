import DataPage from "@/components/shared/DataPage";

export default function EnsemblePage() {
  return <DataPage title="Ensemble" endpoint="/api/ensemble" refreshMs={5000} />;
}
