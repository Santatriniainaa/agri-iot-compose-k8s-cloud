import { Injectable, signal } from '@angular/core';

/**
 * État de connectivité réseau, exposé en signal. Permet à l'interface d'afficher
 * une bannière hors-ligne (la PWA reste utilisable grâce au cache du service worker).
 */
@Injectable({ providedIn: 'root' })
export class ConnectivityService {
  private readonly _online = signal(navigator.onLine);
  readonly online = this._online.asReadonly();

  constructor() {
    window.addEventListener('online', () => this._online.set(true));
    window.addEventListener('offline', () => this._online.set(false));
  }
}
