import { Component } from '@angular/core';

@Component({
  selector: 'adm-forbidden',
  template: `
    <h1>No access</h1>
    <p>Your role does not include this page. Ask a Super Admin if you need access.</p>
  `,
})
export class Forbidden {}
