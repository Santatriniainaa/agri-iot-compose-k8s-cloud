import { DecimalPipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, OnInit, computed, inject, signal } from '@angular/core';
import { MatIconModule } from '@angular/material/icon';

import { ApiService } from '../../core/services/api.service';
import { Weather } from '../../core/models/api.models';

/**
 * Météo du site : conditions courantes issues d'Open-Meteo (via le weather-service
 * → InfluxDB). Icône « héros » déduite de la pluie / couverture nuageuse.
 */
@Component({
  selector: 'app-weather',
  standalone: true,
  imports: [DecimalPipe, MatIconModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <header class="head">
      <h1>Météo du site</h1>
      <button type="button" class="refresh" (click)="load()" [disabled]="loading()"
              aria-label="Rafraîchir">
        <mat-icon>refresh</mat-icon>
      </button>
    </header>

    @if (data(); as w) {
      <section class="hero card">
        <mat-icon class="hero-icon">{{ heroIcon() }}</mat-icon>
        <div class="hero-temp">{{ w.temperature_c | number:'1.0-1' }}<span>°C</span></div>
        <p class="hero-cond">{{ condition() }}</p>
      </section>

      <ul class="grid">
        <li class="card metric">
          <mat-icon>water_drop</mat-icon>
          <span class="v">{{ w.humidity_pct | number:'1.0-0' }} %</span>
          <span class="l">Humidité</span>
        </li>
        <li class="card metric">
          <mat-icon>umbrella</mat-icon>
          <span class="v">{{ w.precipitation_mm | number:'1.0-1' }} mm</span>
          <span class="l">Précipitations</span>
        </li>
        <li class="card metric">
          <mat-icon>air</mat-icon>
          <span class="v">{{ w.wind_speed_ms | number:'1.0-1' }} m/s</span>
          <span class="l">Vent</span>
        </li>
        <li class="card metric">
          <mat-icon>cloud</mat-icon>
          <span class="v">{{ w.cloud_cover_pct | number:'1.0-0' }} %</span>
          <span class="l">Nuages</span>
        </li>
        <li class="card metric">
          <mat-icon>compress</mat-icon>
          <span class="v">{{ w.pressure_hpa | number:'1.0-0' }} hPa</span>
          <span class="l">Pression</span>
        </li>
      </ul>

      <p class="meta">
        @if (w.source) { <span>Source : {{ w.source }}</span> }
        @if (w.time) { <span>{{ formatTime(w.time) }}</span> }
      </p>
    } @else if (loading()) {
      <p class="state">Chargement…</p>
    } @else if (error()) {
      <p class="state error">{{ error() }}</p>
    } @else {
      <p class="state">Aucune donnée météo disponible.</p>
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
      .card { background: var(--color-surface); border-radius: var(--radius); box-shadow: var(--shadow); }
      .hero {
        display: flex; flex-direction: column; align-items: center; gap: 0.25rem;
        padding: 1.5rem 1rem; margin-bottom: 1rem;
      }
      .hero-icon { font-size: 3.5rem; width: 3.5rem; height: 3.5rem; color: var(--color-accent); }
      .hero-temp { font-size: 2.6rem; font-weight: 700; line-height: 1; }
      .hero-temp span { font-size: 1.2rem; color: var(--color-muted); }
      .hero-cond { margin: 0.25rem 0 0; color: var(--color-muted); }
      .grid { list-style: none; margin: 0; padding: 0; display: grid; grid-template-columns: repeat(2, 1fr); gap: 0.6rem; }
      .metric { display: flex; flex-direction: column; align-items: center; gap: 0.15rem; padding: 0.9rem 0.5rem; text-align: center; }
      .metric mat-icon { color: var(--color-primary); }
      .metric .v { font-size: 1.15rem; font-weight: 700; }
      .metric .l { font-size: 0.72rem; color: var(--color-muted); }
      .meta { display: flex; justify-content: space-between; flex-wrap: wrap; gap: 0.5rem; color: var(--color-muted); font-size: 0.75rem; margin: 1rem 0 0; }
      .state { text-align: center; color: var(--color-muted); padding: 2rem 0; }
      .state.error { color: var(--color-danger); }
    `,
  ],
})
export class WeatherComponent implements OnInit {
  private readonly api = inject(ApiService);

  readonly data = signal<Weather | null>(null);
  readonly loading = signal(false);
  readonly error = signal<string | null>(null);

  readonly heroIcon = computed(() => {
    const w = this.data();
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

  readonly condition = computed(() => {
    const w = this.data();
    if (!w) {
      return '';
    }
    if ((w.precipitation_mm ?? 0) > 0.1) {
      return 'Pluie';
    }
    if ((w.cloud_cover_pct ?? 0) > 60) {
      return 'Couvert';
    }
    if ((w.cloud_cover_pct ?? 0) > 25) {
      return 'Partiellement nuageux';
    }
    return 'Ensoleillé';
  });

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.error.set(null);
    this.api.weather().subscribe({
      next: (w) => {
        this.data.set(w);
        this.loading.set(false);
      },
      error: () => {
        this.error.set('Impossible de charger la météo.');
        this.loading.set(false);
      },
    });
  }

  formatTime(ts?: string | null): string {
    if (!ts) {
      return '';
    }
    const d = new Date(ts);
    return Number.isNaN(d.getTime())
      ? ts
      : d.toLocaleString('fr-FR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
  }
}
