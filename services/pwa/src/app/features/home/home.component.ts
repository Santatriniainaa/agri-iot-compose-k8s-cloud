import { Component } from '@angular/core';

/**
 * Écran d'accueil placeholder du scaffold.
 * Remplacé par le dashboard de supervision en Phase 4.
 */
@Component({
  selector: 'app-home',
  standalone: true,
  template: `
    <main class="home">
      <div class="logo">🌱</div>
      <h1>Agri-IoT</h1>
      <p>Supervision mobile des parcelles.</p>
      <p class="muted">PWA en cours de construction — écrans métier en Phase 4.</p>
    </main>
  `,
  styles: [
    `
      .home {
        min-height: 100dvh;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 0.5rem;
        padding: 2rem;
        text-align: center;
      }
      .logo { font-size: 4rem; }
      h1 { margin: 0; color: var(--color-primary-dark); }
      .muted { color: var(--color-muted); font-size: 0.9rem; }
    `,
  ],
})
export class HomeComponent {}
