import { Availability } from '../models/catalog.models';

export const AVAILABILITY_LABEL: Record<Availability, string> = {
  IN_STOCK: 'In stock',
  LOW_STOCK: 'Only a few left',
  OUT_OF_STOCK: 'Out of stock',
};
