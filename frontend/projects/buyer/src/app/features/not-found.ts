import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'buy-not-found',
  imports: [RouterLink],
  template: `<h1>Page not found</h1>
    <p><a routerLink="/">Back to the shop</a></p>`,
})
export class NotFound {}
