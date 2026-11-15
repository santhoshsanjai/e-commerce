import { formatMoney, toMajorUnits, toMinorUnits } from './money.pipe';

describe('money helpers', () => {
  it('formats paise as rupees', () => {
    expect(formatMoney(49900, 'INR')).toBe('₹499.00');
    expect(formatMoney(12345678, 'INR')).toBe('₹1,23,456.78');
  });

  it('converts typed rupees to paise exactly', () => {
    expect(toMinorUnits('499.50')).toBe(49950);
    expect(toMinorUnits('0.29')).toBe(29);
    expect(toMinorUnits('10')).toBe(1000);
    expect(toMinorUnits('19.999')).toBe(1999);
  });

  it('converts paise back for editing', () => {
    expect(toMajorUnits(49950)).toBe('499.50');
  });
});
