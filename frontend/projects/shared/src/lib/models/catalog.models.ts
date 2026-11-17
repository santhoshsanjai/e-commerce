export type ProductStatus = 'DRAFT' | 'PUBLISHED' | 'ARCHIVED';
export type Availability = 'IN_STOCK' | 'LOW_STOCK' | 'OUT_OF_STOCK';
export type ProductSort = 'newest' | 'price_asc' | 'price_desc' | 'name';

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface Category {
  id: string;
  parent_id: string | null;
  name: string;
  slug: string;
  sort_order: number;
  is_active: boolean;
}

export interface Attribute {
  name: string;
  value: string;
}

export interface Media {
  id: string;
  type: 'IMAGE' | 'VIDEO';
  url: string;
  alt_text: string;
  width: number | null;
  height: number | null;
  is_primary: boolean;
  sort_order: number;
}

export interface ProductCard {
  product_number: string;
  name: string;
  slug: string;
  short_description: string;
  price_minor: number;
  compare_at_minor: number | null;
  currency: string;
  availability: Availability;
  image_url: string | null;
  image_alt: string;
  /** The default SKU, used to add the product to the cart. */
  sku_id: string;
}

export interface ProductDetail extends ProductCard {
  description: string;
  category: Category;
  attributes: Attribute[];
  media: Media[];
}

export interface AdminProductListItem {
  id: string;
  product_number: string;
  name: string;
  status: ProductStatus;
  category_name: string;
  price_minor: number;
  currency: string;
  stock_qty: number;
  primary_image_url: string | null;
  updated_at: string;
}

export interface AdminProduct {
  id: string;
  product_number: string;
  name: string;
  slug: string;
  status: ProductStatus;
  category: Category;
  short_description: string;
  description: string;
  /** GST in basis points (1800 = 18%); null uses the shop's default rate. */
  gst_rate_bp: number | null;
  sku: {
    id: string;
    sku: string;
    price_minor: number;
    compare_at_minor: number | null;
    currency: string;
    stock_qty: number;
  };
  attributes: Attribute[];
  media: Media[];
  published_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProductInput {
  name: string;
  category_id: string;
  price_minor: number;
  compare_at_minor: number | null;
  stock_qty: number;
  gst_rate_bp: number | null;
  short_description: string;
  description: string;
  attributes: Attribute[];
}
