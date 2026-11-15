import { Pipe, PipeTransform } from '@angular/core';

const formatters = new Map<string, Intl.NumberFormat>();

/** Format an amount held in minor units (e.g. paise) for display. */
export function formatMoney(minor: number, currency: string, locale = 'en-IN'): string {
  const key = `${locale}:${currency}`;
  let fmt = formatters.get(key);
  if (!fmt) {
    fmt = new Intl.NumberFormat(locale, { style: 'currency', currency });
    formatters.set(key, fmt);
  }
  const digits = fmt.resolvedOptions().maximumFractionDigits ?? 2;
  return fmt.format(minor / 10 ** digits);
}

/** Major units typed by staff (e.g. "499.50") to integer minor units, without float drift. */
export function toMinorUnits(major: string | number, fractionDigits = 2): number {
  const [whole, frac = ''] = String(major).trim().split('.');
  const padded = (frac + '0'.repeat(fractionDigits)).slice(0, fractionDigits);
  return Number(whole || '0') * 10 ** fractionDigits + Number(padded || '0');
}

export function toMajorUnits(minor: number, fractionDigits = 2): string {
  return (minor / 10 ** fractionDigits).toFixed(fractionDigits);
}

@Pipe({ name: 'money' })
export class MoneyPipe implements PipeTransform {
  transform(minor: number | null | undefined, currency: string): string {
    return minor == null ? '' : formatMoney(minor, currency);
  }
}
