import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { AppConfigService } from '../config/app-config.service';
import {
  Alerts,
  Health,
  History,
  Latest,
  Metric,
  Overview,
  Recommendation,
  YieldPrediction,
} from '../models/api.models';

/**
 * Client typé de l'API v1. L'URL de base est résolue au runtime
 * (AppConfigService) ; le JWT est ajouté par l'intercepteur d'authentification.
 */
@Injectable({ providedIn: 'root' })
export class ApiService {
  private readonly http = inject(HttpClient);
  private readonly config = inject(AppConfigService);

  private get base(): string {
    return `${this.config.apiBaseUrl}/api/v1`;
  }

  /** Santé du service (endpoint public, non versionné). */
  health(): Observable<Health> {
    return this.http.get<Health>(`${this.config.apiBaseUrl}/health`);
  }

  /** Vue d'ensemble agrégée : résumé de toutes les parcelles en un appel. */
  overview(): Observable<Overview> {
    return this.http.get<Overview>(`${this.base}/overview`);
  }

  parcels(): Observable<{ parcels: string[] }> {
    return this.http.get<{ parcels: string[] }>(`${this.base}/parcels`);
  }

  latest(parcel: string): Observable<Latest> {
    return this.http.get<Latest>(`${this.base}/latest/${encodeURIComponent(parcel)}`);
  }

  history(parcel: string, metric: Metric, range = '-1h'): Observable<History> {
    const params = new HttpParams().set('metric', metric).set('range', range);
    return this.http.get<History>(`${this.base}/history/${encodeURIComponent(parcel)}`, { params });
  }

  recommend(parcel: string): Observable<Recommendation> {
    return this.http.get<Recommendation>(`${this.base}/recommend/${encodeURIComponent(parcel)}`);
  }

  predictYield(parcel: string): Observable<YieldPrediction> {
    return this.http.get<YieldPrediction>(
      `${this.base}/predict/yield/${encodeURIComponent(parcel)}`,
    );
  }

  alerts(limit = 50): Observable<Alerts> {
    const params = new HttpParams().set('limit', limit);
    return this.http.get<Alerts>(`${this.base}/alerts`, { params });
  }
}
