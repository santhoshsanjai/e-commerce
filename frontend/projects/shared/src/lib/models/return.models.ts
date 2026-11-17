export type ReturnStatus =
  'REQUESTED' | 'APPROVED' | 'REJECTED' | 'RECEIVED' | 'REFUNDED' | 'WITHDRAWN';

export const RETURN_STATUS_LABEL: Record<ReturnStatus, string> = {
  REQUESTED: 'Requested',
  APPROVED: 'Approved',
  REJECTED: 'Not accepted',
  RECEIVED: 'Received',
  REFUNDED: 'Refunded',
  WITHDRAWN: 'Withdrawn',
};

export type ReturnReason =
  'DAMAGED' | 'WRONG_ITEM' | 'NOT_AS_DESCRIBED' | 'NO_LONGER_NEEDED' | 'OTHER';

export const RETURN_REASON_LABEL: Record<ReturnReason, string> = {
  DAMAGED: 'Arrived damaged',
  WRONG_ITEM: 'Wrong item sent',
  NOT_AS_DESCRIBED: 'Not as described',
  NO_LONGER_NEEDED: 'No longer needed',
  OTHER: 'Other',
};

export type RefundMethod = 'UPI' | 'BANK_TRANSFER' | 'CASH' | 'OTHER';

export const REFUND_METHOD_LABEL: Record<RefundMethod, string> = {
  UPI: 'UPI',
  BANK_TRANSFER: 'Bank transfer',
  CASH: 'Cash',
  OTHER: 'Other',
};

export interface ReturnItem {
  order_item_id: string;
  product_number: string;
  product_name: string;
  qty: number;
  unit_price_minor: number;
  restocked: boolean;
}

export interface ReturnRequest {
  return_number: string;
  order_number: string;
  status: ReturnStatus;
  reason: ReturnReason;
  buyer_note: string;
  decision_note: string;
  items: ReturnItem[];
  items_value_minor: number;
  refund_minor: number | null;
  refund_method: RefundMethod | null;
  refund_reference: string;
  currency: string;
  requested_at: string;
  decided_at: string | null;
  received_at: string | null;
  refunded_at: string | null;
}

export interface ReturnEligibility {
  can_request: boolean;
  deadline: string | null;
  reason_not: string;
  current: ReturnRequest | null;
}

export interface AdminReturn extends ReturnRequest {
  id: string;
  order_id: string;
  order_status: string;
  payment_status: 'PENDING' | 'PAID' | 'FAILED' | 'REFUNDED';
  order_total_minor: number;
  customer_name: string;
  customer_email: string;
  ship_phone: string;
}
