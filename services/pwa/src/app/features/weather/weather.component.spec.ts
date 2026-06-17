import { TestBed } from '@angular/core/testing';
import { of } from 'rxjs';

import { WeatherComponent } from './weather.component';
import { ApiService } from '../../core/services/api.service';
import { Weather } from '../../core/models/api.models';

function setup(weather: Weather) {
  TestBed.configureTestingModule({
    imports: [WeatherComponent],
    providers: [{ provide: ApiService, useValue: { weather: () => of(weather) } }],
  });
  const fixture = TestBed.createComponent(WeatherComponent);
  fixture.detectChanges(); // déclenche ngOnInit → load()
  return fixture.componentInstance;
}

describe('WeatherComponent', () => {
  it('déduit la pluie quand il y a des précipitations', () => {
    const c = setup({ precipitation_mm: 2, cloud_cover_pct: 90, temperature_c: 20 });
    expect(c.heroIcon()).toBe('umbrella');
    expect(c.condition()).toBe('Pluie');
  });

  it('déduit « couvert » sous forte nébulosité sans pluie', () => {
    const c = setup({ precipitation_mm: 0, cloud_cover_pct: 80, temperature_c: 22 });
    expect(c.heroIcon()).toBe('cloud');
    expect(c.condition()).toBe('Couvert');
  });

  it('déduit « ensoleillé » par ciel clair', () => {
    const c = setup({ precipitation_mm: 0, cloud_cover_pct: 5, temperature_c: 28 });
    expect(c.heroIcon()).toBe('wb_sunny');
    expect(c.condition()).toBe('Ensoleillé');
  });

  it('charge les données météo au démarrage', () => {
    const c = setup({ temperature_c: 25 });
    expect(c.data()?.temperature_c).toBe(25);
    expect(c.loading()).toBe(false);
  });
});
