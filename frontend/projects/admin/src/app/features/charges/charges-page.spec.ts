import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { API_BASE_URL } from '@shop/shared';
import { Charges, ChargesPage, toPaise, toRupees } from './charges-page';

const URL = '/api/v1/admin/charges';

describe('toPaise / toRupees', () => {
  it('converts typed rupees to paise and back', () => {
    expect(toPaise('49.5')).toBe(4950);
    expect(toPaise(' 40 ')).toBe(4000);
    expect(toPaise('')).toBeNull();
    expect(toPaise('4,000')).toBeNaN();
    expect(toRupees(4000)).toBe('40');
    expect(toRupees(4950)).toBe('49.50');
    expect(toRupees(null)).toBe('');
  });
});

describe('ChargesPage', () => {
  async function setup(current: Charges) {
    TestBed.configureTestingModule({
      imports: [ChargesPage],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: API_BASE_URL, useValue: '/api/v1' },
      ],
    });
    const fixture = TestBed.createComponent(ChargesPage);
    const http = TestBed.inject(HttpTestingController);
    fixture.detectChanges();
    http.expectOne(URL).flush(current);
    await fixture.whenStable();
    fixture.detectChanges();
    await fixture.whenStable();
    return { fixture, http, el: fixture.nativeElement as HTMLElement };
  }

  const CURRENT: Charges = {
    shipping_fee_minor: 4000,
    free_shipping_over_minor: null,
    prices_include_gst: true,
    default_gst_rate_bp: 1800,
  };

  function type(el: HTMLElement, id: string, value: string) {
    const input = el.querySelector<HTMLInputElement>(`#${id}`)!;
    input.value = value;
    input.dispatchEvent(new Event('input'));
  }

  it('shows the current rules and saves them in paise and basis points', async () => {
    const { fixture, http, el } = await setup(CURRENT);
    expect(el.querySelector<HTMLInputElement>('#shipping_fee')!.value).toBe('40');
    expect(el.querySelector<HTMLInputElement>('#gst_rate')!.value).toBe('18');

    type(el, 'free_over', '999');
    type(el, 'gst_rate', '5');
    el.querySelector<HTMLButtonElement>('button[type=submit]')!.click();
    const req = http.expectOne(URL);
    expect(req.request.method).toBe('PUT');
    expect(req.request.body).toEqual({
      ...CURRENT,
      free_shipping_over_minor: 99900,
      default_gst_rate_bp: 500,
    });
    req.flush({ ...CURRENT, free_shipping_over_minor: 99900, default_gst_rate_bp: 500 });
    await fixture.whenStable();
    fixture.detectChanges();
    expect(el.textContent).toContain('Saved.');
  });

  it('refuses free delivery without a charge to waive, without calling the API', async () => {
    const { fixture, http, el } = await setup(CURRENT);
    type(el, 'shipping_fee', '0');
    type(el, 'free_over', '500');
    el.querySelector<HTMLButtonElement>('button[type=submit]')!.click();
    await fixture.whenStable();
    fixture.detectChanges();
    http.expectNone(URL);
    expect(el.querySelector('[role=alert]')!.textContent).toContain('needs a delivery charge');
  });
});
