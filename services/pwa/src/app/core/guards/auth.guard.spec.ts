import { TestBed } from '@angular/core/testing';
import { Router, UrlTree } from '@angular/router';

import { authGuard } from './auth.guard';
import { AuthService } from '../services/auth.service';

function runGuard(url: string) {
  return TestBed.runInInjectionContext(() =>
    authGuard({} as never, { url } as never),
  );
}

describe('authGuard', () => {
  let authed = false;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        { provide: AuthService, useValue: { isAuthenticated: () => authed } },
        {
          provide: Router,
          useValue: { createUrlTree: (cmds: unknown, extras: unknown) => ({ cmds, extras }) as unknown as UrlTree },
        },
      ],
    });
  });

  it('autorise un utilisateur authentifié', () => {
    authed = true;
    expect(runGuard('/parcels')).toBe(true);
  });

  it('redirige vers /login avec returnUrl si non authentifié', () => {
    authed = false;
    const result = runGuard('/parcels') as unknown as { cmds: string[]; extras: { queryParams: { returnUrl: string } } };
    expect(result.cmds).toEqual(['/login']);
    expect(result.extras.queryParams.returnUrl).toBe('/parcels');
  });
});
