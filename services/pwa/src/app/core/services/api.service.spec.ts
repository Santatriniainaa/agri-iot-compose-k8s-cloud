import { TestBed } from '@angular/core/testing';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideHttpClient } from '@angular/common/http';

import { ApiService } from './api.service';
import { AppConfigService } from '../config/app-config.service';

describe('ApiService', () => {
  let api: ApiService;
  let httpMock: HttpTestingController;
  const base = 'http://api.test/api/v1';

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: AppConfigService, useValue: { apiBaseUrl: 'http://api.test' } },
      ],
    });
    api = TestBed.inject(ApiService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('overview appelle /api/v1/overview', () => {
    api.overview().subscribe();
    httpMock.expectOne(`${base}/overview`).flush({ count: 0, irrigating: 0, anomalies: 0, parcels: [] });
  });

  it('weather appelle /api/v1/weather', () => {
    api.weather().subscribe();
    httpMock.expectOne(`${base}/weather`).flush({});
  });

  it('history transmet metric et range en paramètres', () => {
    api.history('zoneA', 'temperature_avg', '-24h').subscribe();
    const req = httpMock.expectOne(
      (r) => r.url === `${base}/history/zoneA` && r.params.get('metric') === 'temperature_avg',
    );
    expect(req.request.params.get('range')).toBe('-24h');
    req.flush({ parcel: 'zoneA', metric: 'temperature_avg', points: [] });
  });

  it('encode le nom de parcelle dans recommend', () => {
    api.recommend('zone A/1').subscribe();
    httpMock.expectOne(`${base}/recommend/zone%20A%2F1`).flush({});
  });

  it('health cible l’endpoint public non versionné', () => {
    api.health().subscribe();
    httpMock.expectOne('http://api.test/health').flush({ status: 'ok', influxdb: true, model_loaded: true });
  });
});
