import { DecimalPipe } from '@angular/common';
import { Component, computed, effect, inject, input, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';

import { ApiService } from '../../core/services/api.service';
import { Metric, Recommendation } from '../../core/models/api.models';
import { LineChartComponent } from '../../shared/line-chart.component';

interface MetricChoice {
  key: Metric;
  label: string;
}

interface RangeChoice {
  key: string;
  label: string;
}

/**
 * Détail d'une parcelle : recommandation d'irrigation + rendement ML prévu,
 * et historique d'une métrique sélectionnable (graphe). Le paramètre de route
 * `parcel` est injecté comme entrée (withComponentInputBinding).
 */
@Component({
  selector: 'app-parcel-detail',
  standalone: true,
  imports: [RouterLink, DecimalPipe, LineChartComponent, MatIconModule],
  template: `
    <header class="head">
      <a routerLink="/parcels" class="back" aria-label="Retour"><mat-icon>arrow_back</mat-icon></a>
      <h1>{{ parcel() }}</h1>
      <button type="button" class="refresh" (click)="reload()" [disabled]="loading()"
              aria-label="Rafraîchir"><mat-icon>refresh</mat-icon></button>
    </header>

    @if (reco(); as r) {
      <section class="card reco" [class.on]="r.irrigation_needed">
        <h2>Recommandation</h2>
        @if (r.irrigation_needed) {
          <p class="action"><mat-icon>water_drop</mat-icon> Irriguer <strong>{{ r.irrigation_minutes | number:'1.0-0' }} min</strong>
            (~{{ r.irrigation_volume_l_m2 | number:'1.0-2' }} L/m²)</p>
        } @else {
          <p class="action ok"><mat-icon>check_circle</mat-icon> Pas d'irrigation nécessaire</p>
        }
        @if (r.anomaly) { <p class="anomaly"><mat-icon>warning</mat-icon> Anomalie capteur détectée</p> }
        @if (r.predicted_yield_index !== null) {
          <p class="yield"><mat-icon>grass</mat-icon> Rendement prévu : <strong>{{ r.predicted_yield_index | number:'1.0-2' }}</strong> / 1</p>
        }
        <ul class="based">
          <li><mat-icon>water_drop</mat-icon> {{ r.based_on.soil_moisture_avg | number:'1.0-1' }}%</li>
          <li><mat-icon>thermostat</mat-icon> {{ r.based_on.temperature_avg | number:'1.0-1' }}°C</li>
          <li><mat-icon>umbrella</mat-icon> {{ r.based_on.rainfall_sum | number:'1.0-1' }} mm</li>
          <li><mat-icon>science</mat-icon> pH {{ r.based_on.soil_ph_avg | number:'1.0-1' }}</li>
        </ul>
      </section>
    }

    <section class="card">
      <h2>Historique</h2>
      <div class="metric-tabs" role="tablist" aria-label="Métrique">
        @for (m of metrics; track m.key) {
          <button type="button" role="tab" [attr.aria-selected]="metric() === m.key"
                  [class.active]="metric() === m.key" (click)="metric.set(m.key)">
            {{ m.label }}
          </button>
        }
      </div>
      <div class="range-tabs" role="tablist" aria-label="Plage de temps">
        @for (r of ranges; track r.key) {
          <button type="button" role="tab" [attr.aria-selected]="range() === r.key"
                  [class.active]="range() === r.key" (click)="range.set(r.key)">
            {{ r.label }}
          </button>
        }
      </div>
      @if (loading()) {
        <p class="state">Chargement…</p>
      } @else {
        <app-line-chart [values]="series()" />
      }
    </section>

    @if (error()) { <p class="state error">{{ error() }}</p> }
  `,
  styles: [
    `
      .head { display: flex; align-items: center; gap: 0.5rem; margin-bottom: 1rem; }
      .head h1 { flex: 1; font-size: 1.4rem; margin: 0; }
      .back, .refresh {
        width: 2.4rem; height: 2.4rem; font-size: 1.2rem; display: inline-flex;
        align-items: center; justify-content: center; background: var(--color-surface);
        box-shadow: var(--shadow); color: var(--color-primary); border-radius: var(--radius);
      }
      .card {
        background: var(--color-surface); border-radius: var(--radius); padding: 1rem;
        box-shadow: var(--shadow); margin-bottom: 1rem;
      }
      .card h2 { font-size: 1rem; margin: 0 0 0.75rem; }
      .reco.on { border-left: 4px solid var(--color-warn); }
      .action { display: flex; align-items: center; gap: 0.35rem; font-size: 1.05rem; margin: 0.25rem 0; }
      .action mat-icon { color: var(--color-accent); }
      .action.ok { color: var(--color-primary-dark); }
      .action.ok mat-icon { color: var(--color-primary); }
      .anomaly { display: flex; align-items: center; gap: 0.35rem; color: var(--color-danger); margin: 0.25rem 0; }
      .yield { display: flex; align-items: center; gap: 0.35rem; margin: 0.25rem 0; }
      .based { list-style: none; display: flex; flex-wrap: wrap; gap: 0.75rem; padding: 0; margin: 0.75rem 0 0; color: var(--color-muted); font-size: 0.9rem; }
      .based li { display: inline-flex; align-items: center; gap: 0.25rem; }
      .based mat-icon, .yield mat-icon, .anomaly mat-icon { font-size: 1.05rem; width: 1.05rem; height: 1.05rem; }
      .based mat-icon { color: var(--color-primary); }
      .metric-tabs, .range-tabs { display: flex; flex-wrap: wrap; gap: 0.4rem; margin-bottom: 0.75rem; }
      .metric-tabs button, .range-tabs button {
        padding: 0.4rem 0.7rem; font-size: 0.8rem; background: #eef3ea; color: var(--color-muted);
      }
      .range-tabs button { padding: 0.3rem 0.6rem; font-size: 0.75rem; }
      .metric-tabs button.active, .range-tabs button.active { background: var(--color-primary); color: #fff; }
      .state { text-align: center; color: var(--color-muted); padding: 1.5rem 0; }
      .state.error { color: var(--color-danger); text-align: center; }
    `,
  ],
})
export class ParcelDetailComponent {
  private readonly api = inject(ApiService);

  readonly parcel = input<string>('');

  readonly metric = signal<Metric>('soil_moisture_avg');
  readonly range = signal<string>('-1h');
  readonly reco = signal<Recommendation | null>(null);
  readonly points = signal<number[]>([]);
  readonly loading = signal(false);
  readonly error = signal<string | null>(null);

  readonly series = computed(() => this.points());

  readonly metrics: MetricChoice[] = [
    { key: 'soil_moisture_avg', label: 'Humidité' },
    { key: 'temperature_avg', label: 'Température' },
    { key: 'soil_ph_avg', label: 'pH' },
    { key: 'rainfall_sum', label: 'Pluie' },
  ];

  readonly ranges: RangeChoice[] = [
    { key: '-1h', label: '1 h' },
    { key: '-24h', label: '24 h' },
    { key: '-7d', label: '7 j' },
  ];

  constructor() {
    // La recommandation ne dépend que de la parcelle.
    effect(() => {
      const parcel = this.parcel();
      if (parcel) {
        this.loadReco(parcel);
      }
    });
    // L'historique dépend de la parcelle, de la métrique et de la plage.
    effect(() => {
      const parcel = this.parcel();
      const metric = this.metric();
      const range = this.range();
      if (parcel) {
        this.loadHistory(parcel, metric, range);
      }
    });
  }

  reload(): void {
    const parcel = this.parcel();
    if (parcel) {
      this.loadReco(parcel);
      this.loadHistory(parcel, this.metric(), this.range());
    }
  }

  private loadReco(parcel: string): void {
    this.api.recommend(parcel).subscribe({
      next: (r) => this.reco.set(r),
      error: () => this.error.set('Recommandation indisponible.'),
    });
  }

  private loadHistory(parcel: string, metric: Metric, range: string): void {
    this.loading.set(true);
    this.error.set(null);
    this.api.history(parcel, metric, range).subscribe({
      next: (h) => {
        this.points.set(h.points.map((p) => p.value ?? 0));
        this.loading.set(false);
      },
      error: () => {
        this.error.set('Historique indisponible.');
        this.loading.set(false);
      },
    });
  }
}
