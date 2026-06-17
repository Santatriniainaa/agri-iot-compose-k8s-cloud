import { DecimalPipe } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { catchError, forkJoin, of } from 'rxjs';

import { ApiService } from '../../core/services/api.service';
import { Overview, Weather } from '../../core/models/api.models';

/**
 * Accueil : vue d'un coup d'œil de l'exploitation — météo du site, KPIs des
 * parcelles et nombre d'alertes — avec accès direct à chaque section.
 */
@Component({
  selector: 'app-home',
  standalone: true,
  imports: [RouterLink, DecimalPipe, MatIconModule],
  template: `
    <header class="head">
      <h1>Accueil</h1>
      <button type="button" class="refresh" (click)="load()" [disabled]="loading()"
              aria-label="Rafraîchir">
        <mat-icon>refresh</mat-icon>
      </button>
    </header>

    @if (weather(); as w) {
      <a class="card weather" routerLink="/weather">
        <mat-icon class="w-icon">{{ heroIcon() }}</mat-icon>
        <div class="w-main">
          <span class="w-temp">{{ w.temperature_c | number:'1.0-0' }}°C</span>
          <span class="w-sub">
            <mat-icon>water_drop</mat-icon>{{ w.humidity_pct | number:'1.0-0' }} %
            · <mat-icon>umbrella</mat-icon>{{ w.precipitation_mm | number:'1.0-1' }} mm
          </span>
        </div>
        <mat-icon class="chevron">chevron_right</mat-icon>
      </a>
    }

    @if (overview(); as ov) {
      <a class="kpis" routerLink="/parcels">
        <div class="kpi"><span class="n">{{ ov.count }}</span><span class="l">parcelles</span></div>
        <div class="kpi warn"><span class="n">{{ ov.irrigating }}</span><span class="l">à irriguer</span></div>
        <div class="kpi danger"><span class="n">{{ ov.anomalies }}</span><span class="l">anomalies</span></div>
      </a>
    }

    <nav class="links">
      <a class="card link" routerLink="/parcels">
        <mat-icon>grid_view</mat-icon><span>Parcelles</span><mat-icon class="chevron">chevron_right</mat-icon>
      </a>
      <a class="card link" routerLink="/alerts">
        <mat-icon>notifications</mat-icon><span>Alertes</span>
        @if (alertsCount() > 0) { <span class="badge">{{ alertsCount() }}</span> }
        <mat-icon class="chevron">chevron_right</mat-icon>
      </a>
    </nav>

    @if (loading() && !overview()) { <p class="state">Chargement…</p> }
    @if (error()) { <p class="state error">{{ error() }}</p> }
  `,
  styles: [
    `
      .head { display: flex; align-items: center; justify-content: space-between; }
      h1 { font-size: 1.4rem; margin: 0.25rem 0 1rem; }
      .refresh {
        width: 2.4rem; height: 2.4rem; display: inline-flex; align-items: center; justify-content: center;
        background: var(--color-surface); box-shadow: var(--shadow); color: var(--color-primary);
      }
      .card { background: var(--color-surface); border-radius: var(--radius); box-shadow: var(--shadow); }
      .weather {
        display: flex; align-items: center; gap: 0.9rem; padding: 1rem; margin-bottom: 1rem; color: var(--color-text);
      }
      .w-icon { font-size: 2.6rem; width: 2.6rem; height: 2.6rem; color: var(--color-accent); }
      .w-main { flex: 1; display: flex; flex-direction: column; }
      .w-temp { font-size: 1.6rem; font-weight: 700; }
      .w-sub { display: flex; align-items: center; gap: 0.2rem; color: var(--color-muted); font-size: 0.85rem; }
      .w-sub mat-icon { font-size: 1rem; width: 1rem; height: 1rem; vertical-align: middle; }
      .chevron { color: var(--color-muted); }
      .kpis { display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.6rem; margin-bottom: 1rem; }
      .kpi {
        background: var(--color-surface); border-radius: var(--radius); padding: 0.8rem 0.5rem;
        text-align: center; box-shadow: var(--shadow); display: flex; flex-direction: column;
      }
      .kpi .n { font-size: 1.5rem; font-weight: 700; }
      .kpi .l { font-size: 0.72rem; color: var(--color-muted); }
      .kpi.warn .n { color: var(--color-warn); }
      .kpi.danger .n { color: var(--color-danger); }
      .links { display: flex; flex-direction: column; gap: 0.7rem; }
      .link { display: flex; align-items: center; gap: 0.7rem; padding: 0.9rem 1rem; color: var(--color-text); }
      .link > span:nth-child(2) { flex: 1; font-weight: 600; }
      .link mat-icon:first-child { color: var(--color-primary); }
      .badge { background: var(--color-danger); color: #fff; font-size: 0.72rem; font-weight: 700; padding: 0.1rem 0.5rem; border-radius: 999px; }
      .state { text-align: center; color: var(--color-muted); padding: 1.5rem 0; }
      .state.error { color: var(--color-danger); }
    `,
  ],
})
export class HomeComponent implements OnInit {
  private readonly api = inject(ApiService);

  readonly overview = signal<Overview | null>(null);
  readonly weather = signal<Weather | null>(null);
  readonly alertsCount = signal(0);
  readonly loading = signal(false);
  readonly error = signal<string | null>(null);

  readonly heroIcon = computed(() => {
    const w = this.weather();
    if (!w) {
      return 'cloud';
    }
    if ((w.precipitation_mm ?? 0) > 0.1) {
      return 'umbrella';
    }
    if ((w.cloud_cover_pct ?? 0) > 60) {
      return 'cloud';
    }
    return 'wb_sunny';
  });

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.error.set(null);
    // Un seul cycle agrégé ; météo et alertes sont tolérantes (null si indisponibles)
    // pour ne pas priver l'accueil des KPIs en cas d'échec partiel.
    forkJoin({
      overview: this.api.overview(),
      weather: this.api.weather().pipe(catchError(() => of(null))),
      alerts: this.api.alerts(50).pipe(catchError(() => of(null))),
    }).subscribe({
      next: ({ overview, weather, alerts }) => {
        this.overview.set(overview);
        this.weather.set(weather);
        this.alertsCount.set(alerts ? (alerts.count ?? alerts.alerts.length) : 0);
        this.loading.set(false);
      },
      error: () => {
        this.error.set('Impossible de charger le tableau de bord.');
        this.loading.set(false);
      },
    });
  }
}
