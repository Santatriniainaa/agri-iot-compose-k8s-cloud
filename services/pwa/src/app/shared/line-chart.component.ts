import { Component, computed, input } from '@angular/core';

/**
 * Mini-graphe en courbe (SVG, sans dépendance externe), adapté au mobile.
 * Trace les `values` normalisées dans un viewBox fixe, avec remplissage dégradé.
 */
@Component({
  selector: 'app-line-chart',
  standalone: true,
  template: `
    @if (line(); as d) {
      <svg viewBox="0 0 300 100" preserveAspectRatio="none" class="chart" role="img"
           [attr.aria-label]="'Courbe de ' + values().length + ' points'">
        <polygon [attr.points]="area()" fill="rgba(46,125,50,0.12)" />
        <polyline [attr.points]="d" fill="none" stroke="var(--color-primary)" stroke-width="2"
                  stroke-linejoin="round" stroke-linecap="round" vector-effect="non-scaling-stroke" />
      </svg>
    } @else {
      <p class="empty">Pas assez de données pour tracer la courbe.</p>
    }
  `,
  styles: [
    `
      .chart { width: 100%; height: 120px; display: block; }
      .empty { color: var(--color-muted); font-size: 0.85rem; text-align: center; padding: 1.5rem 0; }
    `,
  ],
})
export class LineChartComponent {
  readonly values = input<number[]>([]);

  private readonly W = 300;
  private readonly H = 100;

  private readonly coords = computed(() => {
    const v = this.values();
    if (v.length < 2) {
      return null;
    }
    const min = Math.min(...v);
    const max = Math.max(...v);
    const span = max - min || 1;
    const stepX = this.W / (v.length - 1);
    // Marge verticale de 10 % pour éviter de coller aux bords.
    return v.map((value, i) => {
      const x = i * stepX;
      const y = this.H - 10 - ((value - min) / span) * (this.H - 20);
      return { x, y };
    });
  });

  readonly line = computed(() => {
    const pts = this.coords();
    return pts ? pts.map((p) => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ') : null;
  });

  readonly area = computed(() => {
    const pts = this.coords();
    if (!pts) {
      return '';
    }
    const body = pts.map((p) => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ');
    return `0,${this.H} ${body} ${this.W},${this.H}`;
  });
}
