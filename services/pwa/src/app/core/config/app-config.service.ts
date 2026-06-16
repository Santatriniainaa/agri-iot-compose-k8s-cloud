import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { firstValueFrom } from 'rxjs';

import { environment } from '../../../environments/environment';

interface RuntimeConfig {
  apiBaseUrl?: string;
}

/**
 * Configuration résolue au runtime.
 *
 * Charge `config.json` (servi à la racine) au démarrage de l'application : ce
 * fichier est généré par Nginx à partir des variables d'environnement du conteneur,
 * ce qui permet d'utiliser la MÊME image en Compose et en Kubernetes sans recompiler.
 * En l'absence de `config.json` (ex. `ng serve`), on retombe sur `environment`.
 */
@Injectable({ providedIn: 'root' })
export class AppConfigService {
  private readonly http = inject(HttpClient);
  private _apiBaseUrl = environment.apiBaseUrl;

  get apiBaseUrl(): string {
    return this._apiBaseUrl;
  }

  /** Appelé par un app initializer avant le rendu de l'application. */
  async load(): Promise<void> {
    try {
      const cfg = await firstValueFrom(this.http.get<RuntimeConfig>('config.json'));
      if (cfg?.apiBaseUrl) {
        this._apiBaseUrl = cfg.apiBaseUrl.replace(/\/+$/, '');
      }
    } catch {
      // Pas de config.json (dev) → on conserve la valeur d'environnement.
    }
  }
}
