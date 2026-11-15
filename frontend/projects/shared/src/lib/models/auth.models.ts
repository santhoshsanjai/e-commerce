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
  mfa_enabled: boolean;
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

export interface ProfileUpdate {
  full_name?: string;
  /** An empty string clears the number. */
  phone?: string;
}

/** Staff sign-in after the password: signed in, or one more step with the authenticator app. */
export type StaffSignInStep =
  { kind: 'signed-in'; me: Me } | { kind: 'verify' | 'enrol'; challenge: string };

export interface StaffLoginResponse {
  access_token: string | null;
  expires_in: number | null;
  mfa: 'verify' | 'enrol' | null;
  challenge_token: string | null;
}

export interface MfaSetup {
  /** Base32 secret, for typing into the app when the QR code can't be scanned. */
  secret: string;
  otpauth_uri: string;
  /** The QR code as a PNG data: URL. */
  qr_png: string;
}

export interface MfaActivated extends TokenResponse {
  recovery_codes: string[];
}
