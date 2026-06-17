import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';

import { AuthService } from '../../core/services/auth.service';

/** Écran de connexion : authentifie via AuthService puis redirige vers returnUrl. */
@Component({
  selector: 'app-login',
  standalone: true,
  imports: [ReactiveFormsModule, MatIconModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <main class="login">
      <div class="brand">
        <mat-icon class="logo">eco</mat-icon>
        <h1>Agri-IoT</h1>
        <p class="subtitle">Supervision des parcelles</p>
      </div>

      <form [formGroup]="form" (ngSubmit)="submit()" novalidate>
        <label>
          <span>Identifiant</span>
          <input type="text" formControlName="username" autocomplete="username"
                 autocapitalize="none" autocorrect="off" />
        </label>
        <label>
          <span>Mot de passe</span>
          <input type="password" formControlName="password" autocomplete="current-password" />
        </label>

        @if (error()) {
          <p class="error" role="alert">{{ error() }}</p>
        }

        <button type="submit" [disabled]="form.invalid || loading()">
          {{ loading() ? 'Connexion…' : 'Se connecter' }}
        </button>
      </form>
    </main>
  `,
  styles: [
    `
      .login {
        min-height: 100dvh;
        display: flex;
        flex-direction: column;
        justify-content: center;
        gap: 2rem;
        padding: 2rem max(1.25rem, env(safe-area-inset-left));
        max-width: 26rem;
        margin: 0 auto;
      }
      .brand { text-align: center; }
      .logo { font-size: 3.5rem; width: 3.5rem; height: 3.5rem; color: var(--color-primary); }
      h1 { margin: 0.25rem 0 0; color: var(--color-primary-dark); }
      .subtitle { margin: 0; color: var(--color-muted); }
      form { display: flex; flex-direction: column; gap: 1rem; }
      label { display: flex; flex-direction: column; gap: 0.35rem; font-size: 0.9rem; color: var(--color-muted); }
      input {
        padding: 0.85rem 1rem;
        font-size: 1rem;
        border: 1px solid #d4dbcf;
        border-radius: var(--radius);
        background: var(--color-surface);
      }
      input:focus { outline: 2px solid var(--color-primary); border-color: transparent; }
      button {
        margin-top: 0.5rem;
        padding: 0.95rem;
        font-size: 1rem;
        font-weight: 600;
        color: #fff;
        background: var(--color-primary);
      }
      button:disabled { opacity: 0.55; }
      .error { margin: 0; color: var(--color-danger); font-size: 0.9rem; text-align: center; }
    `,
  ],
})
export class LoginComponent {
  private readonly fb = inject(FormBuilder);
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);

  readonly loading = signal(false);
  readonly error = signal<string | null>(null);

  readonly form = this.fb.nonNullable.group({
    username: ['', Validators.required],
    password: ['', Validators.required],
  });

  submit(): void {
    if (this.form.invalid) {
      return;
    }
    this.loading.set(true);
    this.error.set(null);
    const { username, password } = this.form.getRawValue();
    this.auth.login(username, password).subscribe({
      next: () => {
        const returnUrl = this.route.snapshot.queryParamMap.get('returnUrl') ?? '/';
        void this.router.navigateByUrl(returnUrl);
      },
      error: (err) => {
        this.error.set(
          err?.status === 401 ? 'Identifiants invalides.' : 'Connexion impossible. Réessayez.',
        );
        this.loading.set(false);
      },
    });
  }
}
