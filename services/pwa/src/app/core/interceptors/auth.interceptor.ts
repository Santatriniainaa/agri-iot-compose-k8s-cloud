import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, throwError } from 'rxjs';

import { AppConfigService } from '../config/app-config.service';
import { AuthService } from '../services/auth.service';

/**
 * Intercepteur d'authentification :
 *  - ajoute l'en-tête `Authorization: Bearer <jwt>` aux appels vers l'API ;
 *  - sur 401, purge le token et redirige vers l'écran de connexion.
 * La requête de login (qui ne porte pas encore de token) n'est pas modifiée.
 */
export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const auth = inject(AuthService);
  const router = inject(Router);
  const apiBaseUrl = inject(AppConfigService).apiBaseUrl;

  const token = auth.token;
  const isApiCall = req.url.startsWith(apiBaseUrl);
  const isLogin = req.url.endsWith('/auth/login');

  const authReq =
    token && isApiCall && !isLogin
      ? req.clone({ setHeaders: { Authorization: `Bearer ${token}` } })
      : req;

  return next(authReq).pipe(
    catchError((err: HttpErrorResponse) => {
      if (err.status === 401 && !isLogin) {
        auth.logout();
        void router.navigate(['/login']);
      }
      return throwError(() => err);
    }),
  );
};
