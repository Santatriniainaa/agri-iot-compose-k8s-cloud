import { TestBed } from '@angular/core/testing';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideHttpClient } from '@angular/common/http';

import { AuthService } from './auth.service';
import { AppConfigService } from '../config/app-config.service';

const TOKEN_KEY = 'agri_iot_token';

describe('AuthService', () => {
  let service: AuthService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: AppConfigService, useValue: { apiBaseUrl: 'http://api.test' } },
      ],
    });
    service = TestBed.inject(AuthService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('démarre non authentifié sans token stocké', () => {
    expect(service.isAuthenticated()).toBe(false);
    expect(service.token).toBeNull();
  });

  it('login poste un form-urlencoded et persiste le token', () => {
    service.login('agri', 'secret').subscribe();

    const req = httpMock.expectOne('http://api.test/api/v1/auth/login');
    expect(req.request.method).toBe('POST');
    expect(req.request.headers.get('Content-Type')).toBe('application/x-www-form-urlencoded');
    expect(req.request.body).toContain('username=agri');
    req.flush({ access_token: 'jwt-123', token_type: 'bearer' });

    expect(service.isAuthenticated()).toBe(true);
    expect(service.token).toBe('jwt-123');
    expect(localStorage.getItem(TOKEN_KEY)).toBe('jwt-123');
  });

  it('logout purge le token et le localStorage', () => {
    // Authentifie d'abord (le token est posé via login), puis vérifie la purge.
    service.login('agri', 'secret').subscribe();
    httpMock.expectOne('http://api.test/api/v1/auth/login').flush({
      access_token: 'jwt-123',
      token_type: 'bearer',
    });
    expect(service.isAuthenticated()).toBe(true);

    service.logout();
    expect(service.isAuthenticated()).toBe(false);
    expect(localStorage.getItem(TOKEN_KEY)).toBeNull();
  });
});
