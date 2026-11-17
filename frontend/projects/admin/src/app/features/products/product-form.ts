import { Component, computed, inject, input, OnInit, signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import {
  FormArray,
  FormGroup,
  NonNullableFormBuilder,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import {
  AdminProduct,
  apiErrorMessage,
  AuthService,
  HasPermissionDirective,
  ProductInput,
  toMajorUnits,
  toMinorUnits,
} from '@shop/shared';
import { firstValueFrom, Observable } from 'rxjs';
import { AdminCatalogApi } from './admin-catalog.api';
import { StatusChip } from './status-chip';

const MAX_VIDEO_BYTES = 100 * 1024 * 1024;
const MONEY = /^\d{1,9}(\.\d{1,2})?$/;
/** 0 to 40, up to two decimals (e.g. 0.25 for rough diamonds). */
const GST_RATE = /^(40(\.0{1,2})?|[1-3]?\d(\.\d{1,2})?)$/;

/** Create a product, or edit one when an id is in the route. */
@Component({
  selector: 'adm-product-form',
  imports: [ReactiveFormsModule, RouterLink, StatusChip, HasPermissionDirective],
  templateUrl: './product-form.html',
  styleUrl: './product-form.scss',
})
export class ProductForm implements OnInit {
  private readonly api = inject(AdminCatalogApi);
  private readonly router = inject(Router);
  private readonly fb = inject(NonNullableFormBuilder);
  protected readonly auth = inject(AuthService);

  /** Route parameter; undefined on /products/new. */
  readonly id = input<string>();

  protected readonly product = signal<AdminProduct | null>(null);
  protected readonly busy = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly notice = signal<string | null>(null);
  protected readonly categories = toSignal(this.api.categories(), { initialValue: [] });
  protected readonly isNew = computed(() => !this.id());
  protected readonly canEdit = computed(() =>
    this.auth.hasPermission(this.isNew() ? 'products.create' : 'products.update'),
  );

  protected readonly form = this.fb.group({
    name: ['', [Validators.required, Validators.maxLength(200)]],
    category_id: ['', Validators.required],
    price: ['', [Validators.required, Validators.pattern(MONEY)]],
    compare_at: ['', Validators.pattern(MONEY)],
    stock_qty: [0, [Validators.required, Validators.min(0)]],
    /** Percent as typed; blank uses the shop's default rate. */
    gst_rate: ['', Validators.pattern(GST_RATE)],
    short_description: ['', Validators.maxLength(300)],
    description: [''],
    attributes: this.fb.array<FormGroup>([]),
  });
  protected altText = '';

  get attributes(): FormArray<FormGroup> {
    return this.form.controls.attributes;
  }

  async ngOnInit(): Promise<void> {
    const id = this.id();
    if (id) {
      this.load(await firstValueFrom(this.api.product(id)));
    }
    if (!this.canEdit()) {
      this.form.disable();
    }
  }

  protected addAttribute(name = '', value = ''): void {
    this.attributes.push(
      this.fb.group({
        name: [name, [Validators.required, Validators.maxLength(100)]],
        value: [value, [Validators.required, Validators.maxLength(500)]],
      }),
    );
  }

  protected async save(): Promise<void> {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      this.error.set('Check the highlighted fields.');
      return;
    }
    const v = this.form.getRawValue();
    const body: ProductInput = {
      name: v.name,
      category_id: v.category_id,
      price_minor: toMinorUnits(v.price),
      compare_at_minor: v.compare_at ? toMinorUnits(v.compare_at) : null,
      stock_qty: Number(v.stock_qty),
      gst_rate_bp: v.gst_rate === '' ? null : Math.round(Number(v.gst_rate) * 100),
      short_description: v.short_description,
      description: v.description,
      attributes: v.attributes as { name: string; value: string }[],
    };
    const id = this.id();
    const saved = await this.run(
      id ? this.api.updateProduct(id, body) : this.api.createProduct(body),
      'Saved.',
    );
    if (saved && !id) {
      await this.router.navigate(['/products', saved.id], { replaceUrl: true });
    }
  }

  protected async changeStatus(action: 'publish' | 'unpublish' | 'archive'): Promise<void> {
    const id = this.id();
    if (!id) return;
    const messages = {
      publish: 'Published. It is now visible on the shop.',
      unpublish: 'Moved back to draft. It is hidden from the shop.',
      archive: 'Archived.',
    };
    await this.run(this.api.changeStatus(id, action), messages[action]);
  }

  protected async upload(input: HTMLInputElement): Promise<void> {
    const file = input.files?.[0];
    const id = this.id();
    if (!file || !id) return;
    await this.run(this.api.uploadImage(id, file, this.altText), 'Image added.');
    input.value = '';
    this.altText = '';
  }

  protected readonly uploadingVideo = signal(false);

  protected async uploadVideo(input: HTMLInputElement): Promise<void> {
    const file = input.files?.[0];
    const id = this.id();
    if (!file || !id) return;
    if (file.size > MAX_VIDEO_BYTES) {
      this.error.set('Videos must be 100 MB or smaller.');
      input.value = '';
      return;
    }
    this.uploadingVideo.set(true);
    await this.run(this.api.uploadVideo(id, file, this.altText), 'Video added.');
    this.uploadingVideo.set(false);
    input.value = '';
    this.altText = '';
  }

  protected async removeImage(mediaId: string): Promise<void> {
    const id = this.id();
    if (id) await this.run(this.api.deleteMedia(id, mediaId), 'Removed.');
  }

  private async run(call: Observable<AdminProduct>, success: string): Promise<AdminProduct | null> {
    this.busy.set(true);
    this.error.set(null);
    this.notice.set(null);
    try {
      const product = await firstValueFrom(call);
      this.load(product);
      this.notice.set(success);
      return product;
    } catch (err) {
      this.error.set(apiErrorMessage(err));
      return null;
    } finally {
      this.busy.set(false);
    }
  }

  private load(p: AdminProduct): void {
    this.product.set(p);
    this.attributes.clear();
    p.attributes.forEach((a) => this.addAttribute(a.name, a.value));
    this.form.patchValue({
      name: p.name,
      category_id: p.category.id,
      price: toMajorUnits(p.sku.price_minor),
      compare_at: p.sku.compare_at_minor ? toMajorUnits(p.sku.compare_at_minor) : '',
      stock_qty: p.sku.stock_qty,
      gst_rate: p.gst_rate_bp === null ? '' : String(p.gst_rate_bp / 100),
      short_description: p.short_description,
      description: p.description,
    });
    if (p.status === 'ARCHIVED') this.form.disable();
    this.form.markAsPristine();
  }
}
