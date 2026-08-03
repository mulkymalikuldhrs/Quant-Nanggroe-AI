import DataPage from "@/components/shared/DataPage";

export default function FredPage() {
  return <DataPage title="FRED Economic Data" endpoint="/api/fred/series" refreshMs={60000} />;
}
