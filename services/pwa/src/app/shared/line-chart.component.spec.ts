import { ComponentRef } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';

import { LineChartComponent } from './line-chart.component';

describe('LineChartComponent', () => {
  let fixture: ComponentFixture<LineChartComponent>;
  let ref: ComponentRef<LineChartComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({ imports: [LineChartComponent] });
    fixture = TestBed.createComponent(LineChartComponent);
    ref = fixture.componentRef;
  });

  it('ne trace rien avec moins de 2 points', () => {
    ref.setInput('values', [42]);
    fixture.detectChanges();
    expect(fixture.componentInstance.line()).toBeNull();
    expect(fixture.componentInstance.area()).toBe('');
  });

  it('produit une polyline et une aire fermée à partir de plusieurs points', () => {
    ref.setInput('values', [0, 5, 10]);
    fixture.detectChanges();
    const line = fixture.componentInstance.line();
    expect(line).not.toBeNull();
    // 3 points → 3 paires de coordonnées.
    expect(line!.split(' ').length).toBe(3);
    // L'aire commence et finit sur la ligne de base (y = 100).
    const area = fixture.componentInstance.area();
    expect(area.startsWith('0,100')).toBe(true);
    expect(area.endsWith('300,100')).toBe(true);
  });
});
