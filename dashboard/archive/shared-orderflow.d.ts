/** Type declaration for shared OrderFlowMap component */
declare module "@shared/orderflow-map/OrderFlowMap" {
  import { ComponentType } from "react";
  export interface OrderFlowMapProps {
    symbol?: string;
    tick?: number;
    initialMid?: number;
    badge?: string | null;
    badgeClass?: string;
    locale?: string;
  }
  const OrderFlowMap: ComponentType<OrderFlowMapProps>;
  export default OrderFlowMap;
}

declare module "@shared/orderflow-map" {
  export type { OrderFlowMapProps } from "@shared/orderflow-map/OrderFlowMap";
  export { default as OrderFlowMap } from "@shared/orderflow-map/OrderFlowMap";
}
