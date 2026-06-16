import { Component, inject, signal } from '@angular/core';
import { Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { SwUpdate, VersionReadyEvent } from '@angular/service-worker';
import { filter } from 'rxjs';

import { AuthService } from '../core/services/auth.service';
import { ConnectivityService } from '../core/services/connectivity.service';

/**
 * Coquille applicative (zone authentifiée) : en-tête, contenu routé et
 * barre de navigation basse — disposition mobile-first.
 */
@Component({
  selector: 'app-shell',
  standalone: true,
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  template: `
    <header class="topbar">
      <span class="title">🌱 Agri-IoT</span>
      <button class="logout" type="button" (click)="logout()" aria-label="Se déconnecter">⏻</button>
    </header>

    @if (!connectivity.online()) {
      <div class="banner offline" role="status">📡 Hors-ligne — données en cache.</div>
    }
    @if (updateReady()) {
      <button class="banner update" type="button" (click)="applyUpdate()">
        ⬆ Mise à jour disponible — appuyer pour recharger
      </button>
    }

    <section class="content">
      <router-outlet />
    </section>

    <nav class="bottom-nav">
      <a routerLink="/" routerLinkActive="active" [routerLinkActiveOptions]="{ exact: true }">
        <span class="icon">📊</span><span>Parcelles</span>
      </a>
      <a routerLink="/alerts" routerLinkActive="active">
        <span class="icon">🔔</span><span>Alertes</span>
      </a>
    </nav>
  `,
  styles: [
    `
      :host {
        display: flex;
        flex-direction: column;
        min-height: 100dvh;
      }
      .topbar {
        position: sticky;
        top: 0;
        z-index: 10;
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: calc(var(--safe-top) + 0.75rem) 1rem 0.75rem;
        background: var(--color-primary);
        color: #fff;
        box-shadow: var(--shadow);
      }
      .title { font-weight: 700; }
      .logout {
        background: rgba(255, 255, 255, 0.15);
        color: #fff;
        width: 2.25rem;
        height: 2.25rem;
        font-size: 1.1rem;
      }
      .content { flex: 1; padding: 1rem 1rem calc(1rem + var(--safe-bottom)); }
      .bottom-nav {
        position: sticky;
        bottom: 0;
        display: flex;
        background: var(--color-surface);
        border-top: 1px solid #e2e7dd;
        padding-bottom: var(--safe-bottom);
      }
      .bottom-nav a {
        flex: 1;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 0.15rem;
        padding: 0.55rem 0;
        font-size: 0.72rem;
        color: var(--color-muted);
      }
      .bottom-nav a.active { color: var(--color-primary); font-weight: 600; }
      .bottom-nav .icon { font-size: 1.3rem; }
      .banner {
        width: 100%; padding: 0.6rem 1rem; font-size: 0.85rem; text-align: center; border: none;
      }
      .banner.offline { background: #fff3e0; color: var(--color-warn); }
      .banner.update { background: var(--color-accent); color: #fff; font-weight: 600; }
    `,
  ],
})
export class ShellComponent {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  private readonly swUpdate = inject(SwUpdate);
  readonly connectivity = inject(ConnectivityService);

  readonly updateReady = signal(false);

  constructor() {
    // Détecte une nouvelle version mise en cache par le service worker.
    if (this.swUpdate.isEnabled) {
      this.swUpdate.versionUpdates
        .pipe(filter((e): e is VersionReadyEvent => e.type === 'VERSION_READY'))
        .subscribe(() => this.updateReady.set(true));
    }
  }

  applyUpdate(): void {
    void this.swUpdate.activateUpdate().then(() => document.location.reload());
  }

  logout(): void {
    this.auth.logout();
    void this.router.navigate(['/login']);
  }
}
