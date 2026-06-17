import { HttpClient } from '@angular/common/http';
import { Injectable, computed, inject, signal } from '@angular/core';
import { Observable, tap } from 'rxjs';

import { AppConfigService } from '../config/app-config.service';
import { Token } from '../models/api.models';

const TOKEN_KEY = 'agri_iot_token';

/**
 * Authentification : login (OAuth2 password flow), conservation du JWT et état
 * d'authentification réactif (signal). Le token est persisté en localStorage
 * pour survivre au rechargement de la PWA sur mobile.
 */
@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly config = inject(AppConfigService);

  private readonly _token = signal<string | null>(localStorage.getItem(TOKEN_KEY));
  readonly isAuthenticated = computed(() => this._token() !== null);

  get token(): string | null {
    return this._token();
  }

  login(username: string, password: string): Observable<Token> {
    // OAuth2PasswordRequestForm attend un corps x-www-form-urlencoded.
    const body = new URLSearchParams({ username, password });
    return this.http
      .post<Token>(`${this.config.apiBaseUrl}/api/v1/auth/login`, body.toString(), {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      })
      .pipe(tap((res) => this.setToken(res.access_token)));
  }

  logout(): void {
    this._token.set(null);
    localStorage.removeItem(TOKEN_KEY);
  }

  private setToken(token: string): void {
    this._token.set(token);
    localStorage.setItem(TOKEN_KEY, token);
  }
}
