import { Component, OnInit, inject, signal } from '@angular/core';
import { MatIconModule } from '@angular/material/icon';

import { ApiService } from '../../core/services/api.service';
import { AlertItem } from '../../core/models/api.models';

/** Liste des alertes récentes (souscription MQTT côté backend). */
@Component({
  selector: 'app-alerts',
  standalone: true,
  imports: [MatIconModule],
  template: `
    <header class="head">
      <h1>Alertes</h1>
      <button type="button" class="refresh" (click)="load()" [disabled]="loading()"
              aria-label="Rafraîchir"><mat-icon>refresh</mat-icon></button>
    </header>

    @if (items().length) {
      <ul class="list">
        @for (a of items(); track $index) {
          <li class="alert" [class]="a.level ?? 'info'">
            <div class="row">
              <span class="parcel">{{ a.parcel ?? '—' }}</span>
              <span class="time">{{ formatTime(a.ts) }}</span>
            </div>
            <p class="reason">{{ a.reason ?? 'Alerte' }}</p>
            @if (a.recommendation?.action === 'irrigate') {
              <p class="reco"><mat-icon>water_drop</mat-icon> Irriguer {{ a.recommendation?.minutes }} min
                (~{{ a.recommendation?.volume_l_m2 }} L/m²)</p>
            }
          </li>
        }
      </ul>
    } @else if (loading()) {
      <p class="state">Chargement…</p>
    } @else if (error()) {
      <p class="state error">{{ error() }}</p>
    } @else {
      <p class="state">Aucune alerte récente. ✅</p>
    }
  `,
  styles: [
    `
      .head { display: flex; align-items: center; justify-content: space-between; }
      h1 { font-size: 1.4rem; margin: 0.25rem 0 1rem; }
      .refresh {
        width: 2.4rem; height: 2.4rem; display: inline-flex; align-items: center; justify-content: center;
        background: var(--color-surface); box-shadow: var(--shadow); color: var(--color-primary);
      }
      .list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 0.7rem; }
      .alert {
        background: var(--color-surface); border-radius: var(--radius); padding: 0.85rem 1rem;
        box-shadow: var(--shadow); border-left: 4px solid var(--color-muted);
      }
      .alert.warning { border-left-color: var(--color-warn); }
      .alert.critical, .alert.danger { border-left-color: var(--color-danger); }
      .row { display: flex; justify-content: space-between; align-items: baseline; }
      .parcel { font-weight: 700; }
      .time { font-size: 0.75rem; color: var(--color-muted); }
      .reason { margin: 0.4rem 0 0; font-size: 0.9rem; }
      .reco { display: flex; align-items: center; gap: 0.3rem; margin: 0.35rem 0 0; font-size: 0.85rem; color: var(--color-warn); }
      .reco mat-icon { font-size: 1rem; width: 1rem; height: 1rem; }
      .state { text-align: center; color: var(--color-muted); padding: 2rem 0; }
      .state.error { color: var(--color-danger); }
    `,
  ],
})
export class AlertsComponent implements OnInit {
  private readonly api = inject(ApiService);

  readonly items = signal<AlertItem[]>([]);
  readonly loading = signal(false);
  readonly error = signal<string | null>(null);

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.error.set(null);
    this.api.alerts(50).subscribe({
      next: (res) => {
        this.items.set(res.alerts);
        this.loading.set(false);
      },
      error: () => {
        this.error.set('Impossible de charger les alertes.');
        this.loading.set(false);
      },
    });
  }

  formatTime(ts?: string): string {
    if (!ts) {
      return '';
    }
    const d = new Date(ts);
    return Number.isNaN(d.getTime())
      ? ts
      : d.toLocaleString('fr-FR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
  }
}
