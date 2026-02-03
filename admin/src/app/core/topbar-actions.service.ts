import { Injectable, TemplateRef } from '@angular/core';
import { BehaviorSubject } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class TopbarActionsService {
  private actionsSubject = new BehaviorSubject<TemplateRef<any> | null>(null);
  actions$ = this.actionsSubject.asObservable();

  setActions(template: TemplateRef<any> | null) {
    this.actionsSubject.next(template);
  }
}
