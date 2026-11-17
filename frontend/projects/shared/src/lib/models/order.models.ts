export type OrderStatus =
  | 'PENDING_CONFIRMATION'
  | 'CONFIRMED'
  | 'READY_FOR_DISPATCH'
  | 'EXPORTED_TO_COURIER'
  | 'DISPATCHED'
  | 'IN_TRANSIT'
  | 'OUT_FOR_DELIVERY'
  | 'DELIVERED'
  | 'COMPLETED'
  | 'ON_HOLD'
  | 'CANCELLED'
  | 'DELIVERY_FAILED'
  | 'RETURN_IN_TRANSIT'
  | 'RETURNED';

export const ORDER_STATUS_LABEL: Record<OrderStatus, string> = {
  PENDING_CONFIRMATION: 'Awaiting confirmation',
  CONFIRMED: 'Confirmed',
  READY_FOR_DISPATCH: 'Ready for dispatch',
  EXPORTED_TO_COURIER: 'Handed to courier',
  DISPATCHED: 'Dispatched',
  IN_TRANSIT: 'In transit',
  OUT_FOR_DELIVERY: 'Out for delivery',
  DELIVERED: 'Delivered',
  COMPLETED: 'Completed',
  ON_HOLD: 'On hold',
  CANCELLED: 'Cancelled',
  DELIVERY_FAILED: 'Delivery failed',
  RETURN_IN_TRANSIT: 'Returning',
  RETURNED: 'Returned',
};

export type PaymentMethod = 'COD';
export type PaymentStatus = 'PENDING' | 'PAID' | 'FAILED' | 'REFUNDED';

export interface Address {
  id: string;
  recipient_name: string;
  phone: string;
  line1: string;
  line2: string;
  landmark: string;
  city: string;
  region: string;
  postal_code: string;
  country_code: string;
  is_default: boolean;
}

export type AddressInput = Omit<Address, 'id' | 'country_code'>;

export type LineProblem = 'UNAVAILABLE' | 'OUT_OF_STOCK' | 'INSUFFICIENT_STOCK';

export interface CartLine {
  sku_id: string;
  product_number: string;
  product_name: string;
  slug: string;
  image_url: string | null;
  unit_price_minor: number;
  qty: number;
  line_total_minor: number;
  problem: LineProblem | null;
  max_qty: number;
}

export interface Cart {
  items: CartLine[];
  item_count: number;
  subtotal_minor: number;
  shipping_minor: number;
  /** Added to the total; 0 when prices include GST. */
  tax_minor: number;
  /** All GST in the cart, included in prices or added as tax. */
  gst_minor: number;
  prices_include_gst: boolean;
  /** Delivery is free from this subtotal; null when it never is. */
  free_shipping_over_minor: number | null;
  total_minor: number;
  currency: string;
  can_checkout: boolean;
}

export interface OrderItem {
  product_number: string;
  product_name: string;
  sku: string;
  unit_price_minor: number;
  qty: number;
  line_total_minor: number;
  /** Basis points: 1800 = 18%. */
  gst_rate_bp: number;
  gst_minor: number;
}

export interface StatusEvent {
  from_status: OrderStatus | null;
  to_status: OrderStatus;
  source: 'SYSTEM' | 'MANUAL' | 'IMPORT' | 'BUYER';
  reason: string;
  occurred_at: string;
}

export interface OrderSummary {
  order_number: string;
  status: OrderStatus;
  payment_method: PaymentMethod;
  payment_status: PaymentStatus;
  total_minor: number;
  currency: string;
  item_count: number;
  placed_at: string;
}

export interface OrderDetail extends OrderSummary {
  subtotal_minor: number;
  shipping_minor: number;
  tax_minor: number;
  discount_minor: number;
  gst_minor: number;
  prices_include_gst: boolean;
  items: OrderItem[];
  shipping_address: {
    name: string;
    phone: string;
    line1: string;
    line2: string;
    landmark: string;
    city: string;
    region: string;
    postal_code: string;
    country_code: string;
  };
  delivery_instructions: string;
  /** The courier's tracking number, once known. */
  awb_number: string | null;
  timeline: StatusEvent[];
}

export interface AdminOrderListItem extends OrderSummary {
  id: string;
  customer_name: string;
  ship_phone: string;
  ship_city: string;
}

export interface AdminOrderDetail extends OrderDetail {
  id: string;
  customer_name: string;
  customer_email: string;
  /** Statuses the lifecycle allows next; others need the override permission. */
  allowed_next: OrderStatus[];
}

export interface StatusChangeInput {
  status: OrderStatus;
  reason: string;
  override: boolean;
}

export type ImportOutcome = 'will_update' | 'updated' | 'no_change' | 'error';

export interface CourierImportRow {
  row: number;
  order_number: string;
  awb: string;
  courier_status: string;
  current_status: OrderStatus | null;
  new_status: OrderStatus | null;
  outcome: ImportOutcome;
  message: string;
}

export interface CourierImport {
  id: string;
  file_name: string;
  status: 'PREVIEW' | 'CONFIRMED';
  summary: Record<'total' | ImportOutcome, number>;
  uploaded_by_name: string | null;
  created_at: string;
  confirmed_at: string | null;
}

export interface CourierImportDetail extends CourierImport {
  rows: CourierImportRow[];
}

export interface DispatchBatch {
  id: string;
  batch_number: string;
  order_count: number;
  cod_total_minor: number;
  currency: string;
  file_name: string;
  created_by_name: string | null;
  created_at: string;
}

export interface DispatchBatchDetail extends DispatchBatch {
  orders: AdminOrderListItem[];
}
