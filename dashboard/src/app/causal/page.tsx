import DataPage from "@/components/shared/DataPage";

export default function CausalPage() {
  return <DataPage title="Causal Engine (DCC-GARCH)" endpoint="/api/causal" refreshMs={10000} />;
}
