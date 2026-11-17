import { Component, computed, inject } from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';
import { RouterLink } from '@angular/router';
import { AuthService, MoneyPipe, ORDER_STATUS_LABEL, OrderStatus } from '@shop/shared';
import { DashboardApi } from './dashboard.api';
import { SalesChart } from './sales-chart';

const OPEN: OrderStatus[] = [
  'CONFIRMED',
  'READY_FOR_DISPATCH',
  'EXPORTED_TO_COURIER',
  'DISPATCHED',
  'IN_TRANSIT',
  'OUT_FOR_DELIVERY',
  'DELIVERED',
  'DELIVERY_FAILED',
  'ON_HOLD',
  'RETURN_IN_TRANSIT',
];

@Component({
  selector: 'adm-dashboard',
  imports: [RouterLink, MoneyPipe, SalesChart],
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.scss',
})
export class Dashboard {
  private readonly api = inject(DashboardApi);
  protected readonly auth = inject(AuthService);
  protected readonly data = rxResource({ stream: () => this.api.load() });
  protected readonly labels = ORDER_STATUS_LABEL;

  protected readonly openStatuses = computed(() => {
    const counts = this.data.value()?.status_counts;
    return counts ? OPEN.map((s) => ({ status: s, count: counts[s] })) : [];
  });
  protected readonly weekSales = computed(() =>
    (this.data.value()?.last_7_days ?? []).reduce((s, d) => s + d.sales_minor, 0),
  );
  protected readonly nothingToDo = computed(() => {
    const a = this.data.value()?.attention;
    return (
      !!a &&
      !a.awaiting_dispatch &&
      !a.delivery_failed &&
      !a.on_hold &&
      !a.returning &&
      !a.imports_not_applied &&
      !a.returns_open &&
      !a.low_stock.length
    );
  });
  protected can(permission: string): boolean {
    return this.auth.hasPermission(permission);
  }
}
