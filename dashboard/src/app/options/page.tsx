import DataPage from "@/components/shared/DataPage";

export default function OptionsPage() {
  return <DataPage title="Options Analytics" endpoint="/api/options" refreshMs={10000} />;
}
