import { AfterViewInit, Component, ElementRef, HostListener, OnDestroy, OnInit, TemplateRef, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { Subscription } from 'rxjs';
import { JobsService, JobFile, JobSummary, ReportEvent, ReportSummary } from '../../core/jobs.service';
import { TopbarActionsService } from '../../core/topbar-actions.service';
import { AppConfigService } from '../../core/app-config.service';

type ReportStatus = 'queued' | 'running' | 'done' | 'failed';
type ReportType = 'visual' | 'text' | 'both';

interface ReportState {
  reportId: string;
  status: ReportStatus;
  progress: number;
  visualFilename?: string | null;
  textFilename?: string | null;
  bundleFilename?: string | null;
  error?: string | null;
}

@Component({
  selector: 'app-jobs',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="grid" style="grid-template-columns: 1fr 1fr; gap: 16px; align-items: start;">
      <ng-template #topbarActions>
        <div style="display:flex; gap: 8px;">
          <button
            class="btn secondary"
            [style.background]="activeTab === 'dropzone' ? '#f8fafc' : 'var(--theme-secondary)'"
            [style.color]="activeTab === 'dropzone' ? '#0f172a' : 'var(--theme-primary)'"
            [style.border]="activeTab === 'dropzone' ? '1px solid #cbd5f5' : '1px solid var(--theme-primary)'"
            (click)="setTab('dropzone')"
            *ngIf="dropzoneEnabled"
          >Dropzone</button>
          <button
            class="btn secondary"
            [style.background]="activeTab === 'jobs' ? '#f8fafc' : 'var(--theme-secondary)'"
            [style.color]="activeTab === 'jobs' ? '#0f172a' : 'var(--theme-primary)'"
            [style.border]="activeTab === 'jobs' ? '1px solid #cbd5f5' : '1px solid var(--theme-primary)'"
            (click)="setTab('jobs')"
          >Jobs</button>
        </div>
      </ng-template>
      <ng-container *ngIf="activeTab === 'dropzone' && dropzoneEnabled">
        <div style="grid-column: 1 / -1; display:flex; flex-direction:column; gap: 16px;">
          <div
            class="card"
            style="padding: 0; min-height: 260px; width: 100%; max-width: 760px; margin: 0 auto; border: 2px dashed #cbd5f5; background: #f8fafc; display:flex; flex-direction:column; text-align:center;"
            [style.borderColor]="dragActive ? 'var(--theme-primary)' : '#cbd5f5'"
            (dragover)="onDragOver($event)"
            (dragleave)="onDragLeave($event)"
            (drop)="onDrop($event)"
          >
            <div style="flex: 1; display:flex; flex-direction:column; justify-content:center; align-items:center; padding: 12px 16px 8px;">
              <strong>Drop files or folders here</strong>
              <div style="font-size: 13px; color:#475569; margin-top: 6px; max-width: 360px;">
                Single zip (two top-level folders), two folders, or one folder containing two subfolders.
              </div>
              <div style="margin-top: 12px; display:flex; gap: 8px; align-items:center;">
                <button class="btn" (click)="startDropzone()" [disabled]="uploading">Start</button>
              </div>
            </div>
            <div style="padding: 0 16px 12px; text-align:center; min-height: 22px;">
              <span *ngIf="uploading">Uploading...</span>
              <span *ngIf="message" style="color:#166534;">{{ message }}</span>
              <span *ngIf="error" style="color:#b91c1c;">{{ error }}</span>
            </div>
          </div>

          <div class="card" style="padding: 16px; margin: 0 auto; max-width: 760px; width: 100%;">
            <div style="display:flex; justify-content: space-between; align-items:center;">
              <strong>Recent Jobs</strong>
            </div>
            <div *ngIf="recentJobs.length === 0" style="margin-top: 8px; color:#64748b;">No recent jobs.</div>
            <div *ngFor="let job of recentJobs" class="card" style="margin-top: 10px;">
              <div style="display:flex; justify-content: space-between; align-items:center;">
                <div>
                  <strong>{{ job.display_id || job.id }}</strong>
                  <div style="font-size: 12px; color:#64748b; margin-top: 4px;">
                    Set A: {{ job.set_a_label || 'setA' }} · Set B: {{ job.set_b_label || 'setB' }}
                  </div>
                  <div style="font-size: 12px; color:#94a3b8; margin-top: 4px;">
                    Created: {{ formatDate(job.created_at) }}
                  </div>
                </div>
                <div style="display:flex; gap: 8px;">
                  <button
                    class="btn secondary"
                    (click)="openJobDetails(job.id)"
                    [disabled]="job.files_available === false"
                    [attr.title]="job.files_available === false ? retentionMessage : null"
                  >Compare</button>
                  <button
                    class="btn secondary"
                    (click)="handleReportClick(job.id)"
                    [disabled]="isReportBusy(job.id) || job.files_available === false"
                    [attr.title]="job.files_available === false ? retentionMessage : null"
                  >
                    {{ reportButtonLabel(job.id) }}
                  </button>
                  <button
                    class="btn"
                    *ngIf="hasPending(getRecentProgress(job))"
                    (click)="continueJob(job)"
                  >Continue</button>
                </div>
              </div>
              <div *ngIf="getRecentProgress(job) as progress" style="margin-top: 10px;">
                <div style="display:flex; align-items:center; font-size: 12px; color:#475569;">
                  <strong style="flex: 1;">Progress</strong>
                  <span>{{ progress.percent }}%</span>
                </div>
                <div style="height: 8px; width: 100%; background:#e2e8f0; border-radius:999px; overflow:hidden; margin: 6px 0 8px;">
                  <div [style.width.%]="progress.percent" style="height: 100%; background: var(--theme-primary);"></div>
                </div>
                <div style="display:flex; gap: 12px; flex-wrap: wrap; font-size: 12px; color:#475569;">
                  <span>Done: {{ progress.completed }}</span>
                  <span>Running: {{ progress.running }}</span>
                  <span>Pending: {{ progress.pending }}</span>
                  <span>Missing: {{ progress.missing }}</span>
                  <span>Incompatible: {{ progress.incompatible }}</span>
                  <span>Failed: {{ progress.failed }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </ng-container>

      <div *ngIf="activeTab === 'jobs'" class="card" style="grid-column: 1 / -1; max-width: 760px; margin: 0 auto;">
        <div style="display:flex; justify-content: space-between; align-items:center;">
          <h2>Your Jobs</h2>
          <div style="display:flex; gap: 8px;">
            <button class="btn secondary" (click)="clearJobsList()">Clear Jobs</button>
            <button class="btn secondary" (click)="clearJobSelection()">Clear Job</button>
          </div>
        </div>
        <div *ngIf="jobList.length === 0" style="margin-top: 12px;">No jobs yet.</div>
        <div
          *ngFor="let job of jobList"
          class="card"
          style="margin-top: 10px; cursor: pointer;"
          [style.border]="job.id === jobId ? '2px solid var(--theme-primary)' : '1px solid transparent'"
          (click)="selectJob(job.id)"
        >
          <div style="display:flex; justify-content: space-between; align-items:center; gap: 12px;">
            <div>
              <strong>{{ job.display_id || job.id }}</strong>
              <div style="font-size: 12px; color:#64748b; margin-top: 4px;">
                Set A: {{ job.set_a_label || 'setA' }} · Set B: {{ job.set_b_label || 'setB' }}
              </div>
              <div style="font-size: 12px; color:#94a3b8; margin-top: 4px;">
                Created: {{ formatDate(job.created_at) }}
              </div>
            </div>
            <div style="display:flex; gap: 8px; flex-wrap: wrap; justify-content: flex-end;">
              <button
                class="btn secondary"
                (click)="$event.stopPropagation(); openJobDetails(job.id)"
                [disabled]="job.files_available === false"
                [attr.title]="job.files_available === false ? retentionMessage : null"
              >Compare</button>
              <button
                class="btn secondary"
                (click)="$event.stopPropagation(); handleReportClick(job.id)"
                [disabled]="isReportBusy(job.id) || job.files_available === false"
                [attr.title]="job.files_available === false ? retentionMessage : null"
              >{{ reportButtonLabel(job.id) }}</button>
              <button
                class="btn"
                *ngIf="hasPending(job.progress)"
                (click)="$event.stopPropagation(); continueJob(job)"
              >Continue</button>
            </div>
          </div>
          <div *ngIf="job.progress as progress" style="margin-top: 10px; width: 100%;">
            <div style="display:flex; justify-content: space-between; align-items:center; font-size: 12px; color:#475569;">
              <strong>Progress</strong>
              <span>{{ progress.percent }}%</span>
            </div>
            <div style="height: 8px; width: 100%; background:#e2e8f0; border-radius:999px; overflow:hidden; margin: 6px 0 8px;">
              <div [style.width.%]="progress.percent" style="height: 100%; background: var(--theme-primary);"></div>
            </div>
            <div style="display:flex; gap: 12px; flex-wrap: wrap; font-size: 12px; color:#475569;">
              <span>Done: {{ progress.completed }}</span>
              <span>Running: {{ progress.running }}</span>
              <span>Pending: {{ progress.pending }}</span>
              <span>Missing: {{ progress.missing }}</span>
              <span>Incompatible: {{ progress.incompatible }}</span>
              <span>Failed: {{ progress.failed }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="modal-backdrop" *ngIf="reportModalOpen" (click)="closeReportModal()">
      <div
        #reportModal
        class="modal-panel"
        role="dialog"
        aria-modal="true"
        tabindex="-1"
        (click)="$event.stopPropagation()"
      >
        <div class="modal-header">
          <h3>Download report</h3>
          <button class="btn secondary" (click)="closeReportModal()">Close</button>
        </div>
        <div class="modal-sub">Choose what to download for this job.</div>

        <label class="modal-option">
          <input
            type="radio"
            name="reportType"
            value="visual"
            [(ngModel)]="reportTypeSelection"
          />
          <div>
            <div class="modal-option-title">Visual report (PDF)</div>
            <div class="modal-option-desc">Side-by-side page previews with diff highlights and scores.</div>
          </div>
        </label>

        <label class="modal-option">
          <input
            type="radio"
            name="reportType"
            value="text"
            [(ngModel)]="reportTypeSelection"
          />
          <div>
            <div class="modal-option-title">Text diff (patch)</div>
            <div class="modal-option-desc">Unified diff of extracted text, ready for git-style tooling.</div>
          </div>
        </label>

        <label class="modal-option">
          <input
            type="radio"
            name="reportType"
            value="both"
            [(ngModel)]="reportTypeSelection"
          />
          <div>
            <div class="modal-option-title">Both (ZIP)</div>
            <div class="modal-option-desc">Bundle the PDF report and text patch into one zip.</div>
          </div>
        </label>

        <div class="modal-actions">
          <button class="btn secondary" (click)="closeReportModal()">Cancel</button>
          <button class="btn" (click)="confirmReportModal()">Download</button>
        </div>
      </div>
    </div>

  `,
  styles: [
    `
      .modal-backdrop {
        position: fixed;
        inset: 0;
        background: rgba(15, 23, 42, 0.45);
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 16px;
        z-index: 1000;
      }

      .modal-panel {
        width: min(520px, 96vw);
        background: #ffffff;
        border-radius: 16px;
        padding: 20px;
        box-shadow: 0 24px 60px rgba(15, 23, 42, 0.25);
        border: 1px solid #e2e8f0;
      }

      .modal-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 6px;
      }

      .modal-header h3 {
        margin: 0;
        font-size: 18px;
      }

      .modal-sub {
        color: #64748b;
        font-size: 13px;
        margin-bottom: 16px;
      }

      .modal-option {
        display: grid;
        grid-template-columns: auto 1fr;
        gap: 12px;
        align-items: start;
        padding: 12px;
        border-radius: 12px;
        border: 1px solid #e2e8f0;
        background: #f8fafc;
        cursor: pointer;
        margin-bottom: 10px;
      }

      .modal-option input {
        margin-top: 4px;
      }

      .modal-option-title {
        font-weight: 600;
        color: #0f172a;
      }

      .modal-option-desc {
        color: #64748b;
        font-size: 12px;
        margin-top: 4px;
      }

      .modal-actions {
        display: flex;
        justify-content: flex-end;
        gap: 8px;
        margin-top: 18px;
      }
    `
  ]
})
export class JobsComponent implements OnInit, AfterViewInit, OnDestroy {
  @ViewChild('topbarActions', { static: true }) topbarActionsTpl!: TemplateRef<any>;
  @ViewChild('reportModal') reportModal?: ElementRef<HTMLDivElement>;
  activeTab: 'dropzone' | 'jobs' = 'dropzone';
  dropzoneEnabled = true;
  private jobsSub?: Subscription;
  private reportSub?: Subscription;
  get selectedJob() {
    return this.jobList.find(job => job.id === this.jobId) || null;
  }
  get recentJobs() {
    return this.jobList.slice(0, 4);
  }
  private dropFilesA: { file: File; relPath: string }[] = [];
  private dropFilesB: { file: File; relPath: string }[] = [];
  jobId = '';
  files: JobFile[] = [];
  jobList: JobSummary[] = [];
  filesA: File[] = [];
  filesB: File[] = [];
  zipFile: File | null = null;
  setALabel: string | null = null;
  setBLabel: string | null = null;
  dragActive = false;
  uploadStripSegments = 1;
  uploading = false;
  message = '';
  error = '';
  jobProgress: import('../../core/jobs.service').JobProgress | null = null;
  recentProgress: Record<string, import('../../core/jobs.service').JobProgress> = {};
  reportStateByJobId: Record<string, ReportState> = {};
  retentionMessage = 'Files are kept for a limited time. After cleanup, comparisons and reports are not available.';
  reportModalOpen = false;
  reportModalJobId = '';
  reportModalReportId = '';
  reportTypeSelection: ReportType = 'visual';
  private lastFocusedElement: HTMLElement | null = null;

  constructor(
    private jobsService: JobsService,
    private topbar: TopbarActionsService,
    private router: Router,
    private config: AppConfigService
  ) {}

  ngOnInit() {
    this.config.getConfig().subscribe({
      next: cfg => {
        this.dropzoneEnabled = cfg.enable_dropzone;
        if (!this.dropzoneEnabled && this.activeTab === 'dropzone') {
          this.activeTab = 'jobs';
        }
      },
      error: () => {
        this.dropzoneEnabled = true;
      }
    });
    this.loadJobs();
    this.jobsSub = this.jobsService.watchJobs().subscribe({
      next: jobs => {
        this.jobList = this.sortJobs(jobs);
        this.refreshRecentProgressForMissing();
      }
    });
    this.reportSub = this.jobsService.watchReports().subscribe({
      next: event => {
        this.applyReportEvent(event);
      }
    });
  }

  setTab(tab: 'dropzone' | 'jobs') {
    if (tab === 'dropzone' && !this.dropzoneEnabled) {
      this.activeTab = 'jobs';
      return;
    }
    this.activeTab = tab;
  }

  ngAfterViewInit() {
    setTimeout(() => this.topbar.setActions(this.topbarActionsTpl), 0);
  }

  ngOnDestroy() {
    this.jobsSub?.unsubscribe();
    this.reportSub?.unsubscribe();
    this.topbar.setActions(null);
  }

  startUpload() {
    this.message = '';
    this.error = '';
    this.uploading = true;
    this.jobsService.createJob().subscribe({
      next: (job: { id: string }) => {
        this.jobId = job.id;
        const uploadA = this.dropFilesA.length
          ? this.jobsService.uploadFolderWithPaths(job.id, 'A', this.dropFilesA)
          : this.jobsService.uploadFolder(job.id, 'A', this.filesA, this.uploadStripSegments);
        uploadA.subscribe({
          next: () => {
            const uploadB = this.dropFilesB.length
              ? this.jobsService.uploadFolderWithPaths(job.id, 'B', this.dropFilesB)
              : this.jobsService.uploadFolder(job.id, 'B', this.filesB, this.uploadStripSegments);
            uploadB.subscribe({
              next: () => {
                this.jobsService.startJob(job.id, this.setALabel, this.setBLabel).subscribe({
                  next: () => {
                    this.uploading = false;
                    this.message = 'Upload complete. Job started.';
                    this.loadJobs();
                    this.loadFiles();
                  },
                  error: (err: any) => {
                    this.uploading = false;
                    this.error = this.formatError(err, 'Failed to start job.');
                  }
                });
              },
              error: (err: any) => {
                this.uploading = false;
                this.error = this.formatError(err, 'Failed to upload Set B.');
              }
            });
          },
          error: (err: any) => {
            this.uploading = false;
            this.error = this.formatError(err, 'Failed to upload Set A.');
          }
        });
      },
      error: (err: any) => {
        this.uploading = false;
        this.error = this.formatError(err, 'Failed to create job.');
      }
    });
  }

  startZipUpload() {
    if (!this.zipFile) return;
    this.message = '';
    this.error = '';
    this.uploading = true;
    this.jobsService.createJob().subscribe({
      next: (job: { id: string }) => {
        this.jobId = job.id;
        this.jobsService.uploadZipSets(job.id, this.zipFile as File).subscribe({
          next: () => {
            this.jobsService.startJob(job.id, this.setALabel, this.setBLabel).subscribe({
              next: () => {
                this.uploading = false;
                this.message = 'Zip upload complete. Job started.';
                this.loadJobs();
                this.loadFiles();
              },
              error: (err: any) => {
                this.uploading = false;
                this.error = this.formatError(err, 'Failed to start job.');
              }
            });
          },
          error: (err: any) => {
            this.uploading = false;
            this.error = this.formatError(err, 'Failed to upload zip.');
          }
        });
      },
      error: (err: any) => {
        this.uploading = false;
        this.error = this.formatError(err, 'Failed to create job.');
      }
    });
  }

  startDropzone() {
    if (this.zipFile) {
      this.startZipUpload();
      return;
    }
    if (this.filesA.length > 0 && this.filesB.length > 0) {
      this.startUpload();
      return;
    }
    this.error = 'Drop files or folders first.';
  }

  onDragOver(event: DragEvent) {
    event.preventDefault();
    this.dragActive = true;
  }

  onDragLeave(event: DragEvent) {
    event.preventDefault();
    this.dragActive = false;
  }

  onDrop(event: DragEvent) {
    event.preventDefault();
    this.dragActive = false;
    this.message = '';
    this.error = '';
    this.handleDrop(event);
  }

  private async handleDrop(event: DragEvent) {
    const rawFiles = Array.from(event.dataTransfer?.files || []);
    const fileEntries = rawFiles.map(file => ({
      file,
      relPath: (file as any).webkitRelativePath || file.name
    }));
    const hasRelPaths = fileEntries.some(item => item.relPath.includes('/'));
    const items = event.dataTransfer?.items;
    const dropped = !hasRelPaths && items ? await this.readDroppedItems(items) : [];
    const files = (hasRelPaths
      ? fileEntries
      : dropped.length
        ? dropped
        : fileEntries).map(item => ({
          file: item.file,
          relPath: item.relPath.replace(/\\/g, '/')
        }));

    if (files.length === 0) {
      this.error = 'No files detected in drop.';
      return;
    }

    if (files.length === 1 && files[0].file.name.toLowerCase().endsWith('.zip')) {
      this.zipFile = files[0].file;
      this.filesA = [];
      this.filesB = [];
      this.dropFilesA = [];
      this.dropFilesB = [];
      this.uploadStripSegments = 1;
      this.setALabel = null;
      this.setBLabel = null;
      this.message = `Zip selected: ${files[0].file.name}`;
      return;
    }

    const pdfFiles = files.filter(item => this.isPdfFile(item.file, item.relPath));
    if (pdfFiles.length === 0) {
      this.error = 'No PDF files detected in drop.';
      return;
    }

    const relPaths = pdfFiles.map(item => item.relPath);
    const hasFolders = relPaths.some(path => path.includes('/'));
    if (!hasFolders) {
      this.error = 'Please drop folders or a zip file.';
      return;
    }

    const topFolders = Array.from(new Set(relPaths.map(path => path.split('/')[0]).filter(Boolean)));

    if (topFolders.length >= 2) {
      const [aFolder, bFolder] = topFolders;
      this.setALabel = aFolder;
      this.setBLabel = bFolder;
      this.dropFilesA = pdfFiles
        .filter(item => item.relPath.startsWith(`${aFolder}/`))
        .map(item => ({ file: item.file, relPath: this.stripPath(item.relPath, 1) }));
      this.dropFilesB = pdfFiles
        .filter(item => item.relPath.startsWith(`${bFolder}/`))
        .map(item => ({ file: item.file, relPath: this.stripPath(item.relPath, 1) }));
      this.filesA = this.dropFilesA.map(item => item.file);
      this.filesB = this.dropFilesB.map(item => item.file);
      this.zipFile = null;
      this.uploadStripSegments = 1;
      this.message = `Detected two folders: ${aFolder} and ${bFolder}`;
      return;
    }

    if (topFolders.length === 1) {
      const secondFolders = Array.from(
        new Set(
          relPaths
            .map(path => path.split('/')[1])
            .filter(Boolean)
        )
      );

      if (secondFolders.length >= 2) {
        const [aFolder, bFolder] = secondFolders;
        this.setALabel = aFolder;
        this.setBLabel = bFolder;
        this.dropFilesA = pdfFiles
          .filter(item => item.relPath.includes(`/${aFolder}/`))
          .map(item => ({ file: item.file, relPath: this.stripPath(item.relPath, 2) }));
        this.dropFilesB = pdfFiles
          .filter(item => item.relPath.includes(`/${bFolder}/`))
          .map(item => ({ file: item.file, relPath: this.stripPath(item.relPath, 2) }));
        this.filesA = this.dropFilesA.map(item => item.file);
        this.filesB = this.dropFilesB.map(item => item.file);
        this.zipFile = null;
        this.uploadStripSegments = 2;
        this.message = `Detected subfolders: ${aFolder} and ${bFolder}`;
        return;
      }
    }

    this.error = 'Could not detect two sets. Drop two folders or a folder with two subfolders.';
  }

  private stripPath(path: string, segments: number) {
    const parts = path.replace(/\\/g, '/').split('/');
    return parts.slice(segments).join('/') || parts[parts.length - 1];
  }

  private isPdfFile(file: File, relPath: string) {
    const name = (relPath || file.name).toLowerCase();
    return name.endsWith('.pdf');
  }

  private readDroppedItems(items: DataTransferItemList): Promise<{ file: File; relPath: string }[]> {
    const entries: any[] = [];
    for (let i = 0; i < items.length; i++) {
      const item = items[i];
      const entry = (item as any).webkitGetAsEntry?.();
      if (entry) entries.push(entry);
    }
    if (!entries.length) return Promise.resolve([]);
    return this.readEntries(entries);
  }

  private async readEntries(entries: any[], prefix = ''): Promise<{ file: File; relPath: string }[]> {
    const results: { file: File; relPath: string }[] = [];
    for (const entry of entries) {
      const items = await this.readEntry(entry, prefix);
      results.push(...items);
    }
    return results;
  }

  private async readEntry(entry: any, prefix: string): Promise<{ file: File; relPath: string }[]> {
    if (entry.isFile) {
      return new Promise(resolve => {
        entry.file((file: File) => resolve([{ file, relPath: `${prefix}${entry.name}` }]));
      });
    }

    if (entry.isDirectory) {
      const reader = entry.createReader();
      const allEntries: any[] = [];
      const readAll = (): Promise<any[]> =>
        new Promise(resolve => {
          reader.readEntries((batch: any[]) => {
            if (!batch.length) {
              resolve(allEntries);
              return;
            }
            allEntries.push(...batch);
            readAll().then(resolve);
          });
        });

      const children = await readAll();
      return this.readEntries(children, `${prefix}${entry.name}/`);
    }

    return [];
  }

  private formatError(err: any, fallback: string) {
    const detail = err?.error?.detail;
    if (!detail) return fallback;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) {
      return detail.map(item => item?.msg ?? JSON.stringify(item)).join(', ');
    }
    return JSON.stringify(detail);
  }

  loadFiles() {
    if (!this.jobId) return;
    this.jobsService.listFiles(this.jobId).subscribe((files: JobFile[]) => (this.files = files));
    this.loadProgress();
  }

  loadJobs() {
    this.jobsService.listJobs().subscribe((jobs: JobSummary[]) => {
      this.jobList = this.sortJobs(jobs);
      this.refreshRecentProgressForMissing();
    });
    this.jobsService.listReports().subscribe({
      next: reports => {
        this.applyReportSummaries(reports);
      },
      error: () => {
        // ignore report list failures
      }
    });
  }

  getRecentProgress(job: JobSummary) {
    return job.progress || this.recentProgress[job.id] || null;
  }

  private refreshRecentProgressForMissing() {
    const ids = this.recentJobs
      .filter(job => !job.progress)
      .map(job => job.id);
    if (ids.length === 0) return;
    ids.forEach(jobId => {
      this.jobsService.getJobProgress(jobId).subscribe({
        next: progress => {
          this.recentProgress = { ...this.recentProgress, [jobId]: progress };
        },
        error: () => {
          // ignore missing progress
        }
      });
    });
  }
  
  private sortJobs(jobs: JobSummary[]) {
    return [...jobs].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
  }

  hasPending(progress: import('../../core/jobs.service').JobProgress | null | undefined) {
    return !!progress && (progress.pending ?? 0) > 0;
  }

  continueJob(job: JobSummary) {
    this.message = '';
    this.error = '';
    this.jobsService.continueJob(job.id).subscribe({
      next: () => {
        this.message = 'Job continued.';
        this.loadJobs();
        if (this.jobId === job.id) {
          this.loadFiles();
        }
      },
      error: (err: any) => {
        this.error = this.formatError(err, 'Failed to continue job.');
      }
    });
  }

  selectJob(jobId: string) {
    this.jobId = jobId;
    this.loadFiles();
  }

  openJobDetails(jobId: string) {
    this.jobsService.listFiles(jobId).subscribe({
      next: files => {
        if (files.length > 0) {
          this.router.navigate(['/jobs', jobId, 'files', files[0].id]);
        } else {
          this.setTab('jobs');
          this.selectJob(jobId);
          this.message = 'No files available for this job yet.';
        }
      },
      error: () => {
        this.setTab('jobs');
        this.selectJob(jobId);
        this.error = 'Failed to load job files.';
      }
    });
  }

  openJobTextDetails(jobId: string) {
    this.jobsService.listFiles(jobId).subscribe({
      next: files => {
        if (files.length > 0) {
          this.router.navigate(['/jobs', jobId, 'files', files[0].id, 'text']);
        } else {
          this.setTab('jobs');
          this.selectJob(jobId);
          this.message = 'No files available for this job yet.';
        }
      },
      error: () => {
        this.setTab('jobs');
        this.selectJob(jobId);
        this.error = 'Failed to load job files.';
      }
    });
  }

  handleReportClick(jobId: string) {
    const state = this.reportStateByJobId[jobId];
    if (state?.status === 'done') {
      this.openReportModal(jobId, state.reportId);
      return;
    }
    if (!state || state.status === 'failed') {
      this.requestReport(jobId);
    }
  }

  reportButtonLabel(jobId: string) {
    const state = this.reportStateByJobId[jobId];
    if (!state) return 'Report';
    if (state.status === 'queued') return 'Queued...';
    if (state.status === 'running') return state.progress ? `Generating ${state.progress}%` : 'Generating...';
    if (state.status === 'failed') return 'Retry Report';
    return 'Download';
  }

  isReportBusy(jobId: string) {
    const state = this.reportStateByJobId[jobId];
    return state?.status === 'queued' || state?.status === 'running';
  }

  openReportModal(jobId: string, reportId: string) {
    this.reportModalJobId = jobId;
    this.reportModalReportId = reportId;
    this.reportTypeSelection = 'visual';
    this.reportModalOpen = true;
    this.lastFocusedElement = document.activeElement as HTMLElement | null;
    setTimeout(() => this.reportModal?.nativeElement.focus(), 0);
  }

  closeReportModal() {
    this.reportModalOpen = false;
    this.reportModalJobId = '';
    this.reportModalReportId = '';
    if (this.lastFocusedElement) {
      this.lastFocusedElement.focus();
    }
  }

  confirmReportModal() {
    if (!this.reportModalReportId) {
      return;
    }
    const jobId = this.reportModalJobId;
    const reportId = this.reportModalReportId;
    const reportType = this.reportTypeSelection;
    this.reportModalOpen = false;
    this.reportModalJobId = '';
    this.reportModalReportId = '';
    this.downloadReportById(reportId, jobId, reportType);
  }

  @HostListener('document:keydown', ['$event'])
  onDocumentKeydown(event: KeyboardEvent) {
    if (!this.reportModalOpen) {
      return;
    }
    if (event.key === 'Escape') {
      event.preventDefault();
      this.closeReportModal();
      return;
    }
    if (event.key === 'Enter') {
      event.preventDefault();
      this.confirmReportModal();
      return;
    }
    if (event.key === 'Tab') {
      this.trapModalFocus(event);
    }
  }

  private trapModalFocus(event: KeyboardEvent) {
    const modal = this.reportModal?.nativeElement;
    if (!modal) {
      return;
    }
    const focusables = Array.from(
      modal.querySelectorAll<HTMLElement>(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      )
    ).filter(el => !el.hasAttribute('disabled'));

    if (focusables.length === 0) {
      event.preventDefault();
      modal.focus();
      return;
    }

    const first = focusables[0];
    const last = focusables[focusables.length - 1];
    const active = document.activeElement as HTMLElement | null;

    if (event.shiftKey && (active === first || active === modal)) {
      event.preventDefault();
      last.focus();
      return;
    }
    if (!event.shiftKey && active === last) {
      event.preventDefault();
      first.focus();
    }
  }

  private requestReport(jobId: string) {
    this.message = '';
    this.error = '';
    this.jobsService.createReport(jobId).subscribe({
      next: (report: ReportSummary) => {
        this.reportStateByJobId = {
          ...this.reportStateByJobId,
          [jobId]: this.toReportState(report)
        };
        this.message = 'Report queued.';
      },
      error: (err: any) => {
        this.error = this.formatError(err, 'Failed to queue report.');
      }
    });
  }

  private downloadReportById(reportId: string, jobId: string, reportType: ReportType) {
    const state = this.reportStateByJobId[jobId];
    this.message = '';
    this.error = '';
    this.jobsService.downloadReport(reportId, reportType).subscribe({
      next: (resp) => {
        const blob = resp.body as Blob;
        const disposition = resp.headers.get('content-disposition');
        const filename = this.getReportFilename(disposition, state, jobId, reportType);
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        this.message = 'Report downloaded successfully.';
      },
      error: (err: any) => {
        this.error = this.formatError(err, 'Failed to download report.');
      }
    });
  }

  private getReportFilename(
    disposition: string | null,
    state: ReportState | undefined,
    jobId: string,
    reportType: ReportType
  ) {
    if (disposition) {
      const match = /filename="?([^";]+)"?/i.exec(disposition);
      if (match?.[1]) {
        return match[1];
      }
    }
    if (reportType === 'text') {
      if (state?.textFilename) {
        return state.textFilename;
      }
      return `text-diff-${jobId}.patch`;
    }
    if (reportType === 'both') {
      if (state?.bundleFilename) {
        return state.bundleFilename;
      }
      return `pdfdiff-reports-${jobId}.zip`;
    }
    if (state?.visualFilename) {
      return state.visualFilename;
    }
    return `diff-report-${jobId}.pdf`;
  }

  private applyReportEvent(event: ReportEvent) {
    this.reportStateByJobId = {
      ...this.reportStateByJobId,
      [event.source_job_id]: {
        reportId: event.report_id,
        status: event.status,
        progress: event.progress,
        visualFilename: event.visual_filename ?? null,
        textFilename: event.text_filename ?? null,
        bundleFilename: event.bundle_filename ?? null,
        error: event.error ?? null
      }
    };
  }

  private applyReportSummaries(reports: ReportSummary[]) {
    const sorted = [...reports].sort(
      (a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
    );
    const next: Record<string, ReportState> = { ...this.reportStateByJobId };
    for (const report of sorted) {
      if (!next[report.source_job_id]) {
        next[report.source_job_id] = this.toReportState(report);
      }
    }
    this.reportStateByJobId = next;
  }

  private toReportState(report: ReportSummary): ReportState {
    return {
      reportId: report.id,
      status: report.status,
      progress: report.progress,
      visualFilename: report.visual_filename ?? null,
      textFilename: report.text_filename ?? null,
      bundleFilename: report.bundle_filename ?? null,
      error: report.error ?? null
    };
  }

  loadProgress() {
    if (!this.jobId) {
      this.jobProgress = null;
      return;
    }
    this.jobsService.getJobProgress(this.jobId).subscribe({
      next: progress => {
        this.jobProgress = progress;
      },
      error: () => {
        this.jobProgress = null;
      }
    });
  }

  clearJobSelection() {
    if (!this.jobId) return;
    this.message = '';
    this.error = '';
    const targetId = this.jobId;
    this.jobsService.deleteJob(targetId).subscribe({
      next: () => {
        this.jobId = '';
        this.files = [];
        this.jobProgress = null;
        this.message = 'Job removed.';
        this.loadJobs();
      },
      error: (err: any) => {
        this.error = this.formatError(err, 'Failed to remove job.');
      }
    });
  }

  clearJobsList() {
    this.message = '';
    this.error = '';
    this.jobsService.clearJobs().subscribe({
      next: (res) => {
        this.clearJobSelection();
        const deleted = res?.deleted ?? 0;
        this.message = `Jobs cleared (${deleted}).`;
        this.loadJobs();
      },
      error: (err: any) => {
        this.error = this.formatError(err, 'Failed to clear jobs.');
      }
    });
  }

  badgeClass(file: JobFile) {
    if (file.missing_in_set_a || file.missing_in_set_b) return 'badge warn';
    return 'badge success';
  }

  statusBadge(status: string) {
    if (status === 'completed') return 'badge success';
    if (status === 'failed' || status === 'cancelled') return 'badge danger';
    if (status === 'running') return 'badge warn';
    return 'badge neutral';
  }

  formatDate(value: string) {
    if (!value) return '';
    const date = new Date(value);
    return isNaN(date.getTime()) ? value : date.toLocaleString();
  }
}
