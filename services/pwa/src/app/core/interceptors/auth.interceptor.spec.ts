import { TestBed } from '@angular/core/testing';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { HttpClient, provideHttpClient, withInterceptors } from '@angular/common/http';
import { Router } from '@angular/router';

import { authInterceptor } from './auth.interceptor';
import { AuthService } from '../services/auth.service';
import { AppConfigService } from '../config/app-config.service';

describe('authInterceptor', () => {
  let http: HttpClient;
  let httpMock: HttpTestingController;
  let logoutCalled: boolean;
  let navigated: unknown[];

  beforeEach(() => {
    logoutCalled = false;
    navigated = [];
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(withInterceptors([authInterceptor])),
        provideHttpClientTesting(),
        { provide: AppConfigService, useValue: { apiBaseUrl: 'http://api.test' } },
        { provide: AuthService, useValue: { token: 'jwt-123', logout: () => (logoutCalled = true) } },
        { provide: Router, useValue: { navigate: (c: unknown[]) => navigated.push(c) } },
      ],
    });
    http = TestBed.inject(HttpClient);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('ajoute l’en-tête Authorization aux appels API', () => {
    http.get('http://api.test/api/v1/overview').subscribe();
    const req = httpMock.expectOne('http://api.test/api/v1/overview');
    expect(req.request.headers.get('Authorization')).toBe('Bearer jwt-123');
    req.flush({});
  });

  it('ne porte pas le token sur la requête de login', () => {
    http.post('http://api.test/api/v1/auth/login', null).subscribe();
    const req = httpMock.expectOne('http://api.test/api/v1/auth/login');
    expect(req.request.headers.has('Authorization')).toBe(false);
    req.flush({});
  });

  it('sur 401 purge la session et redirige vers /login', () => {
    http.get('http://api.test/api/v1/overview').subscribe({ error: () => undefined });
    httpMock.expectOne('http://api.test/api/v1/overview').flush(null, { status: 401, statusText: 'Unauthorized' });
    expect(logoutCalled).toBe(true);
    expect(navigated).toContainEqual(['/login']);
  });
});
