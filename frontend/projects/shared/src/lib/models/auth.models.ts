export type UserType = 'BUYER' | 'STAFF';

/** Login audience: buyers use the public site, staff use the admin portal. */
export type Audience = 'buyer' | 'staff';

export interface TokenResponse {
  access_token: string;
  token_type: 'bearer';
  expires_in: number;
}

export interface Me {
  id: string;
  email: string;
  full_name: string;
  phone: string | null;
  user_type: UserType;
  roles: string[];
  permissions: string[];
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest extends LoginRequest {
  full_name: string;
  phone?: string | null;
}

/** Error envelope returned by every API failure. */
export interface ApiErrorBody {
  error: {
    code: string;
    message: string;
    details: unknown;
    request_id: string | null;
  };
}
