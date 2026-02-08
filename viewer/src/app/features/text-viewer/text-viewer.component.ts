import { AfterViewInit, Component, ElementRef, OnDestroy, OnInit, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { catchError, finalize, forkJoin, of } from 'rxjs';
import loader from '@monaco-editor/loader';
import type * as Monaco from 'monaco-editor';
import { JobsService, JobFile, JobSummary } from '../../core/jobs.service';
import { TopbarActionsService } from '../../core/topbar-actions.service';

@Component({
  selector: 'app-text-viewer',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="card">
      <div class="viewer-header" style="display:flex; justify-content: space-between; align-items:center; margin-bottom: 12px;">
        <div style="display:flex; align-items:center; gap: 12px;">
          <button class="btn secondary" (click)="backToJobs()">Back</button>
          <h2 style="margin:0;" *ngIf="!currentFile">Text Comparison</h2>
          <h2 style="margin:0;" *ngIf="currentFile">{{ currentFile.relative_path }}</h2>
        </div>
        <div style="display:flex; align-items:center; gap: 8px;">
          <button class="btn secondary" (click)="goToVisual()">Visual Compare</button>
          <button class="btn secondary" (click)="prevDiff()" [disabled]="!hasDiffs">Prev Diff</button>
          <button class="btn" (click)="nextDiff()" [disabled]="!hasDiffs">Next Diff</button>
        </div>
      </div>

      <div *ngIf="loadError" style="margin-bottom: 12px; color: #c62828;">
        {{ loadError }}
      </div>

      <div class="grid" style="grid-template-columns: 320px 1fr; gap: 16px; align-items: start; flex: 1; min-height: 0;" *ngIf="!loadError">
        <div class="card" style="padding: 12px; overflow:auto;">
          <div style="display:flex; justify-content: space-between; align-items:center; margin-bottom: 8px;">
            <strong>Files</strong>
            <span style="font-size: 12px; color:#64748b;">{{ files.length }}</span>
          </div>
          <table style="width:100%; border-collapse: collapse; font-size: 12px; margin: 0 auto;">
            <thead>
              <tr style="text-align:left; color:#64748b;">
                <th style="padding: 6px 4px;">File</th>
                <th style="padding: 6px 4px;">Status</th>
              </tr>
            </thead>
            <tbody>
              <tr
                *ngFor="let file of files"
                (click)="openFile(file)"
                [style.background]="file.id === fileId ? 'var(--theme-secondary)' : 'transparent'"
                style="cursor:pointer;"
              >
                <td style="padding: 6px 4px; word-break: break-word;">
                  {{ file.relative_path }}
                </td>
                <td style="padding: 6px 4px;">
                  <span class="badge" [ngClass]="fileStatusBadge(file)">
                    {{ (file.status || (file.missing_in_set_a || file.missing_in_set_b ? 'missing' : 'ready')) | titlecase }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div style="display: flex; flex-direction: column; flex: 1; min-height: 0; position: relative; overflow: hidden;">
          <div *ngIf="textNotice" style="margin-bottom: 8px; color:#64748b;">
            {{ textNotice }}
          </div>
          <div *ngIf="textLoading" style="margin-bottom: 8px; color:#475569;">Loading text...</div>
          <div #diffContainer class="text-diff"></div>
        </div>
      </div>
    </div>
  `,
  styles: [
    `
      .text-diff {
        height: 70vh;
        min-height: 360px;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        overflow: hidden;
      }
    `
  ]
})
export class TextViewerComponent implements OnInit, AfterViewInit, OnDestroy {
  @ViewChild('diffContainer', { static: false }) diffContainer?: ElementRef<HTMLDivElement>;

  jobId = '';
  fileId = '';
  job: JobSummary | null = null;
  files: JobFile[] = [];
  private filesWs?: { unsubscribe: () => void };
  loadError = '';
  textLoading = false;
  textNotice = '';
  hasDiffs = false;

  private monaco?: typeof Monaco;
  private diffEditor?: Monaco.editor.IStandaloneDiffEditor;
  private modelA?: Monaco.editor.ITextModel;
  private modelB?: Monaco.editor.ITextModel;
  private diffChanges: Monaco.editor.ILineChange[] = [];
  private diffIndex = -1;
  private latestTextA = '';
  private latestTextB = '';
  private diffListener?: Monaco.IDisposable;

  constructor(
    private route: ActivatedRoute,
    private jobs: JobsService,
    private router: Router,
    private topbar: TopbarActionsService
  ) {}

  ngOnInit(): void {
    this.route.paramMap.subscribe(params => {
      const nextJobId = params.get('jobId') || '';
      const nextFileId = params.get('fileId') || '';
      const jobChanged = nextJobId !== this.jobId;
      const fileChanged = nextFileId !== this.fileId;
      this.jobId = nextJobId;
      this.fileId = nextFileId;

      setTimeout(() => {
        if (jobChanged) {
          this.loadJob();
          this.loadJobFiles();
          this.subscribeJobFiles();
        }
        if (fileChanged) {
          this.loadFileText();
        }
      }, 0);
    });
  }

  ngAfterViewInit(): void {
    this.initEditor();
  }

  get currentFile(): JobFile | null {
    return this.files.find(f => f.id === this.fileId) || null;
  }

  loadJob() {
    if (!this.jobId) return;
    this.jobs.getJob(this.jobId).subscribe({
      next: job => {
        this.job = job;
        setTimeout(() => this.topbar.setJobTitle(job.display_id), 0);
      },
      error: () => {
        this.job = null;
        setTimeout(() => this.topbar.setJobTitle(null), 0);
      }
    });
  }

  loadJobFiles() {
    if (!this.jobId) return;
    this.jobs.listFiles(this.jobId).subscribe({
      next: files => {
        this.files = files;
      },
      error: () => {
        this.files = [];
      }
    });
  }

  subscribeJobFiles() {
    if (!this.jobId) return;
    this.filesWs?.unsubscribe();
    this.filesWs = this.jobs.watchJobFiles(this.jobId).subscribe({
      next: files => {
        this.files = files;
      }
    });
  }

  openFile(file: JobFile) {
    if (!file?.id) return;
    this.router.navigate(['/jobs', this.jobId, 'files', file.id, 'text']);
  }

  fileStatusBadge(file: JobFile) {
    const status = (file.status || (file.missing_in_set_a || file.missing_in_set_b ? 'missing' : 'ready')).toLowerCase();
    if (status === 'running' || status === 'pending') return 'badge warn';
    if (status === 'failed' || status === 'incompatible') return 'badge danger';
    if (status === 'missing') return 'badge warn';
    if (status === 'completed') return 'badge success';
    return 'badge neutral';
  }

  backToJobs() {
    this.router.navigate(['/jobs']);
  }

  goToVisual() {
    if (!this.jobId || !this.fileId) return;
    this.router.navigate(['/jobs', this.jobId, 'files', this.fileId]);
  }

  private async initEditor() {
    if (!this.diffContainer) return;
    loader.config({ paths: { vs: '/assets/monaco/vs' } });
    this.monaco = await loader.init();
    this.diffEditor = this.monaco.editor.createDiffEditor(this.diffContainer.nativeElement, {
      automaticLayout: true,
      readOnly: true,
      renderSideBySide: true,
      wordWrap: 'on',
      minimap: { enabled: false },
      renderOverviewRuler: false,
      scrollBeyondLastLine: false
    });
    this.diffListener = this.diffEditor.onDidUpdateDiff(() => {
      this.refreshDiffs();
    });
    this.applyTextToEditor();
  }

  private applyTextToEditor() {
    if (!this.monaco || !this.diffEditor) return;
    this.modelA?.dispose();
    this.modelB?.dispose();
    this.modelA = this.monaco.editor.createModel(this.latestTextA || '', 'text/plain');
    this.modelB = this.monaco.editor.createModel(this.latestTextB || '', 'text/plain');
    this.diffEditor.setModel({ original: this.modelA, modified: this.modelB });
    this.refreshDiffs();
  }

  private refreshDiffs() {
    if (!this.diffEditor) return;
    this.diffChanges = this.diffEditor.getLineChanges() || [];
    this.diffIndex = this.diffChanges.length ? 0 : -1;
    this.hasDiffs = this.diffChanges.length > 0;
  }

  private loadFileText() {
    if (!this.jobId || !this.fileId) return;
    this.loadError = '';
    this.textLoading = true;
    this.textNotice = '';

    let missingA = false;
    let missingB = false;

    const textA$ = this.jobs.getFileText(this.jobId, this.fileId, 'A').pipe(
      catchError(() => {
        missingA = true;
        return of('');
      })
    );

    const textB$ = this.jobs.getFileText(this.jobId, this.fileId, 'B').pipe(
      catchError(() => {
        missingB = true;
        return of('');
      })
    );

    forkJoin([textA$, textB$])
      .pipe(finalize(() => (this.textLoading = false)))
      .subscribe({
        next: ([textA, textB]) => {
          this.latestTextA = textA || '';
          this.latestTextB = textB || '';
          this.applyTextToEditor();
          if (missingA && missingB) {
            this.textNotice = 'Text not available for either set yet.';
          } else if (missingA) {
            this.textNotice = 'Set A text not available yet.';
          } else if (missingB) {
            this.textNotice = 'Set B text not available yet.';
          }
        },
        error: () => {
          this.loadError = 'Failed to load text for this file.';
        }
      });
  }

  nextDiff() {
    if (!this.diffChanges.length) return;
    this.diffIndex = (this.diffIndex + 1) % this.diffChanges.length;
    this.revealDiff(this.diffChanges[this.diffIndex]);
  }

  prevDiff() {
    if (!this.diffChanges.length) return;
    this.diffIndex = (this.diffIndex - 1 + this.diffChanges.length) % this.diffChanges.length;
    this.revealDiff(this.diffChanges[this.diffIndex]);
  }

  private revealDiff(change: Monaco.editor.ILineChange) {
    if (!this.diffEditor) return;
    const modifiedLine = change.modifiedStartLineNumber || change.modifiedEndLineNumber || 1;
    const originalLine = change.originalStartLineNumber || change.originalEndLineNumber || 1;
    const originalEditor = this.diffEditor.getOriginalEditor();
    const modifiedEditor = this.diffEditor.getModifiedEditor();
    originalEditor.revealLineInCenter(originalLine);
    modifiedEditor.revealLineInCenter(modifiedLine);
  }

  ngOnDestroy(): void {
    this.filesWs?.unsubscribe();
    this.topbar.setJobTitle(null);
    this.modelA?.dispose();
    this.modelB?.dispose();
    this.diffListener?.dispose();
    this.diffEditor?.dispose();
  }
}
