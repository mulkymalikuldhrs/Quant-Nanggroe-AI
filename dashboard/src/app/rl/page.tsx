import DataPage from "@/components/shared/DataPage";

export default function RlPage() {
  return <DataPage title="Reinforcement Learning" endpoint="/api/rl" refreshMs={15000} />;
}
