import { DecimalPipe } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { ApiService } from '../../core/services/api.service';
import { Overview } from '../../core/models/api.models';

/**
 * Tableau de bord : vue d'ensemble de toutes les parcelles en un seul appel
 * (`/api/v1/overview`). Pull-to-refresh tactile + bouton de rafraîchissement.
 */
@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [RouterLink, DecimalPipe],
  template: `
    <div
      class="ptr"
      (touchstart)="onTouchStart($event)"
      (touchmove)="onTouchMove($event)"
      (touchend)="onTouchEnd()"
    >
      @if (pull() > 0) {
        <div class="ptr-indicator" [style.height.px]="pull()">
          {{ pull() > threshold ? '↑ Relâcher' : '↓ Tirer' }}
        </div>
      }

      <header class="head">
        <h1>Parcelles</h1>
        <button type="button" class="refresh" (click)="load()" [disabled]="loading()">⟳</button>
      </header>

      @if (data(); as ov) {
        <div class="kpis">
          <div class="kpi"><span class="n">{{ ov.count }}</span><span class="l">actives</span></div>
          <div class="kpi warn"><span class="n">{{ ov.irrigating }}</span><span class="l">à irriguer</span></div>
          <div class="kpi danger"><span class="n">{{ ov.anomalies }}</span><span class="l">anomalies</span></div>
        </div>

        <ul class="cards">
          @for (p of ov.parcels; track p.parcel) {
            <li>
              <a class="card" [routerLink]="['/parcel', p.parcel]">
                <div class="card-head">
                  <span class="name">{{ p.parcel }}</span>
                  <span class="badges">
                    @if (p.irrigation_needed) { <span class="badge warn">💧 {{ p.irrigation_minutes | number:'1.0-0' }} min</span> }
                    @if (p.anomaly) { <span class="badge danger">⚠ anomalie</span> }
                  </span>
                </div>
                <div class="metrics">
                  <span>💧 {{ p.soil_moisture_avg | number:'1.0-1' }}%</span>
                  <span>🌡 {{ p.temperature_avg | number:'1.0-1' }}°C</span>
                  <span>🧪 pH {{ p.soil_ph_avg | number:'1.0-1' }}</span>
                  @if (p.predicted_yield_index !== null) {
                    <span>🌾 {{ p.predicted_yield_index | number:'1.0-2' }}</span>
                  }
                </div>
              </a>
            </li>
          } @empty {
            <li class="empty">Aucune parcelle active.</li>
          }
        </ul>
      } @else if (loading()) {
        <p class="state">Chargement…</p>
      }

      @if (error()) {
        <p class="state error">{{ error() }}</p>
      }
    </div>
  `,
  styles: [
    `
      .ptr { position: relative; }
      .ptr-indicator {
        display: flex;
        align-items: center;
        justify-content: center;
        color: var(--color-muted);
        font-size: 0.85rem;
        overflow: hidden;
        transition: height 0.1s ease;
      }
      .head { display: flex; align-items: center; justify-content: space-between; }
      h1 { font-size: 1.4rem; margin: 0.25rem 0 1rem; }
      .refresh {
        width: 2.4rem; height: 2.4rem; font-size: 1.2rem;
        background: var(--color-surface); box-shadow: var(--shadow); color: var(--color-primary);
      }
      .kpis { display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.6rem; margin-bottom: 1rem; }
      .kpi {
        background: var(--color-surface); border-radius: var(--radius); padding: 0.8rem 0.5rem;
        text-align: center; box-shadow: var(--shadow); display: flex; flex-direction: column;
      }
      .kpi .n { font-size: 1.5rem; font-weight: 700; }
      .kpi .l { font-size: 0.72rem; color: var(--color-muted); }
      .kpi.warn .n { color: var(--color-warn); }
      .kpi.danger .n { color: var(--color-danger); }
      .cards { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 0.7rem; }
      .card {
        display: block; background: var(--color-surface); border-radius: var(--radius);
        padding: 0.9rem 1rem; box-shadow: var(--shadow); color: var(--color-text);
      }
      .card-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.5rem; }
      .name { font-weight: 700; font-size: 1.05rem; }
      .badges { display: flex; gap: 0.35rem; flex-wrap: wrap; }
      .badge { font-size: 0.7rem; padding: 0.2rem 0.5rem; border-radius: 999px; background: #eef3ea; }
      .badge.warn { background: #fff3e0; color: var(--color-warn); }
      .badge.danger { background: #ffebee; color: var(--color-danger); }
      .metrics { display: flex; flex-wrap: wrap; gap: 0.75rem; font-size: 0.9rem; color: var(--color-muted); }
      .state { text-align: center; color: var(--color-muted); padding: 2rem 0; }
      .state.error { color: var(--color-danger); }
      .empty { text-align: center; color: var(--color-muted); padding: 1.5rem 0; }
    `,
  ],
})
export class DashboardComponent implements OnInit {
  private readonly api = inject(ApiService);

  readonly data = signal<Overview | null>(null);
  readonly loading = signal(false);
  readonly error = signal<string | null>(null);

  readonly threshold = 70;
  readonly pull = signal(0);
  private startY = 0;
  private pulling = false;

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.error.set(null);
    this.api.overview().subscribe({
      next: (ov) => {
        this.data.set(ov);
        this.loading.set(false);
      },
      error: () => {
        this.error.set('Impossible de charger les parcelles.');
        this.loading.set(false);
      },
    });
  }

  onTouchStart(ev: TouchEvent): void {
    if (window.scrollY === 0 && !this.loading()) {
      this.startY = ev.touches[0].clientY;
      this.pulling = true;
    }
  }

  onTouchMove(ev: TouchEvent): void {
    if (!this.pulling) {
      return;
    }
    const delta = ev.touches[0].clientY - this.startY;
    this.pull.set(delta > 0 ? Math.min(delta / 2, 100) : 0);
  }

  onTouchEnd(): void {
    if (this.pulling && this.pull() > this.threshold) {
      this.load();
    }
    this.pulling = false;
    this.pull.set(0);
  }
}
