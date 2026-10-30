/**
 * Centralized Currency Formatting Utility for MenuMind AI.
 * Handles localized currencies (INR ₹, USD $, EUR €, GBP £).
 */

export interface CurrencyOptions {
  currency?: string;
  minimumFractionDigits?: number;
  maximumFractionDigits?: number;
  compact?: boolean;
}

export function formatCurrency(
  amount: number | string | null | undefined,
  options?: CurrencyOptions | string
): string {
  if (amount === null || amount === undefined || isNaN(Number(amount))) {
    return '₹0';
  }

  const num = Number(amount);
  const opts: CurrencyOptions = typeof options === 'string' ? { currency: options } : (options || {});
  const currencySymbol = opts.currency || '₹';

  // Format with Indian numbering system if INR
  if (currencySymbol === '₹' || currencySymbol === 'INR') {
    if (opts.compact && Math.abs(num) >= 100000) {
      if (Math.abs(num) >= 10000000) {
        return `₹${(num / 10000000).toFixed(2)} Cr`;
      }
      return `₹${(num / 100000).toFixed(2)} L`;
    }

    const minDigits = opts.minimumFractionDigits !== undefined ? opts.minimumFractionDigits : 0;
    const maxDigits = opts.maximumFractionDigits !== undefined ? opts.maximumFractionDigits : 2;

    const formattedNum = num.toLocaleString('en-IN', {
      minimumFractionDigits: minDigits,
      maximumFractionDigits: maxDigits,
    });
    return `₹${formattedNum}`;
  }

  // Standard international formatting
  return `${currencySymbol}${num.toLocaleString('en-US', {
    minimumFractionDigits: opts.minimumFractionDigits ?? 2,
    maximumFractionDigits: opts.maximumFractionDigits ?? 2,
  })}`;
}
