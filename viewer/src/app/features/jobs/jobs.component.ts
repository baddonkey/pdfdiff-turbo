import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { JobsService, JobFile, JobSummary, SampleSet } from '../../core/jobs.service';

@Component({
  selector: 'app-jobs',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
    <div class="grid" style="grid-template-columns: 1fr 1fr; gap: 16px;">
      <div class="card">
      <h2>Upload</h2>
      <div
        class="card"
        style="height: 220px; border: 2px dashed #cbd5f5; background: #f8fafc; display:flex; flex-direction:column; justify-content:center; align-items:center; text-align:center;"
        [style.borderColor]="dragActive ? '#2563eb' : '#cbd5f5'"
        (dragover)="onDragOver($event)"
        (dragleave)="onDragLeave($event)"
        (drop)="onDrop($event)"
      >
        <strong>Drop files or folders here</strong>
        <div style="font-size: 13px; color:#475569; margin-top: 6px; max-width: 360px;">
          Single zip (two top-level folders), two folders, or one folder containing two subfolders.
        </div>
        <div style="margin-top: 12px; display:flex; gap: 8px; align-items:center;">
          <button class="btn" (click)="startDropzone()" [disabled]="uploading">Start</button>
        </div>
      </div>

      <div class="grid" style="grid-template-columns: 1fr; gap: 16px; margin-top: 16px;">
        <div>
          <label>Set A folder</label>
          <input class="input" type="file" webkitdirectory (change)="onFolderChange($event, 'A')" />
        </div>
        <div>
          <label>Set B folder</label>
          <input class="input" type="file" webkitdirectory (change)="onFolderChange($event, 'B')" />
        </div>
        <div>
          <label>Zip with two top-level folders</label>
          <input class="input" type="file" accept=".zip" (change)="onZipChange($event)" />
        </div>
        <div>
          <label>Sample set</label>
          <select class="input" [(ngModel)]="selectedSample">
            <option value="">Select sample…</option>
            <option *ngFor="let sample of samples" [value]="sample.name">{{ sample.name }}</option>
          </select>
        </div>
        <div style="display:flex; gap: 12px; align-items:center; flex-wrap: wrap;">
          <button class="btn" (click)="startUpload()" [disabled]="uploading || filesA.length === 0 || filesB.length === 0">Upload & Start</button>
          <button class="btn secondary" (click)="startZipUpload()" [disabled]="uploading || !zipFile">Upload Zip & Start</button>
          <button class="btn secondary" (click)="startSampleUpload()" [disabled]="uploading || !selectedSample">Use Sample & Start</button>
          <span *ngIf="uploading">Uploading...</span>
          <span *ngIf="message" style="color:#166534;">{{ message }}</span>
          <span *ngIf="error" style="color:#b91c1c;">{{ error }}</span>
        </div>
      </div>
      </div>

      <div class="card">
        <div style="display:flex; justify-content: space-between; align-items:center;">
          <h2>Your Jobs</h2>
          <div style="display:flex; gap: 8px;">
            <button class="btn secondary" (click)="loadJobs()">Refresh</button>
            <button class="btn secondary" (click)="clearJobsList()">Clear Jobs</button>
            <button class="btn secondary" (click)="clearJobSelection()">Clear Job</button>
          </div>
        </div>
        <div *ngIf="jobList.length === 0" style="margin-top: 12px;">No jobs yet.</div>
        <div *ngFor="let job of jobList" class="card" style="margin-top: 12px;">
          <div style="display:flex; justify-content: space-between; align-items:center;">
            <div>
              <strong>{{ job.id }}</strong>
              <div>
                <span class="badge" [ngClass]="statusBadge(job.status)">{{ job.status }}</span>
              </div>
            </div>
            <div style="display:flex; gap: 8px;">
              <button class="btn secondary" (click)="selectJob(job.id)">View Files</button>
              <button class="btn" (click)="startComparison(job.id)">Start Comparison</button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="card" style="margin-top:16px;">
      <h2>Job Files</h2>
      <div *ngIf="jobProgress" style="margin-bottom: 12px;">
        <div style="display:flex; justify-content: space-between; align-items:center;">
          <strong>Progress</strong>
          <span>{{ jobProgress.percent }}%</span>
        </div>
        <div style="height: 8px; background:#e2e8f0; border-radius:999px; overflow:hidden; margin: 6px 0 8px;">
          <div [style.width.%]="jobProgress.percent" style="height: 100%; background:#2563eb;"></div>
        </div>
        <div style="display:flex; gap: 12px; flex-wrap: wrap; font-size: 12px; color:#475569;">
          <span>Done: {{ jobProgress.completed }}</span>
          <span>Running: {{ jobProgress.running }}</span>
          <span>Pending: {{ jobProgress.pending }}</span>
          <span>Missing: {{ jobProgress.missing }}</span>
          <span>Incompatible: {{ jobProgress.incompatible }}</span>
          <span>Failed: {{ jobProgress.failed }}</span>
        </div>
      </div>
      <div class="grid" style="grid-template-columns: 220px 1fr; gap: 20px;">
        <div>
          <label>Job ID</label>
          <input class="input" [(ngModel)]="jobId" placeholder="Paste job id" />
          <button class="btn" (click)="loadFiles()">Load Files</button>
        </div>
        <div>
          <div *ngIf="files.length === 0">No files loaded.</div>
          <div *ngFor="let file of files" class="card" style="margin-bottom: 12px;">
            <div style="display:flex; justify-content: space-between; align-items: center;">
              <div>
                <strong>{{ file.relative_path }}</strong>
                <div>
                  <span class="badge" [ngClass]="badgeClass(file)">
                    {{ file.missing_in_set_a || file.missing_in_set_b ? 'Missing' : 'Ready' }}
                  </span>
                </div>
              </div>
              <a class="btn" [routerLink]="['/jobs', jobId, 'files', file.id]">Open</a>
            </div>
          </div>
        </div>
      </div>
    </div>
  `
})
export class JobsComponent implements OnInit {
  private dropFilesA: { file: File; relPath: string }[] = [];
  private dropFilesB: { file: File; relPath: string }[] = [];
  jobId = '';
  files: JobFile[] = [];
  jobList: JobSummary[] = [];
  filesA: File[] = [];
  filesB: File[] = [];
  zipFile: File | null = null;
  samples: SampleSet[] = [];
  selectedSample = '';
  dragActive = false;
  uploadStripSegments = 1;
  uploading = false;
  message = '';
  error = '';
  jobProgress: import('../../core/jobs.service').JobProgress | null = null;

  constructor(private jobsService: JobsService) {}

  ngOnInit() {
    this.loadJobs();
    this.loadSamples();
  }

  onFolderChange(event: Event, setName: 'A' | 'B') {
    const input = event.target as HTMLInputElement;
    const list = input.files ? Array.from(input.files) : [];
    if (setName === 'A') {
      this.filesA = list;
    } else {
      this.filesB = list;
    }
    this.dropFilesA = [];
    this.dropFilesB = [];
  }

  onZipChange(event: Event) {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0] || null;
    this.zipFile = file;
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
                this.jobsService.startJob(job.id).subscribe({
                  next: () => {
                    this.uploading = false;
                    this.message = 'Upload complete. Job started.';
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
            this.jobsService.startJob(job.id).subscribe({
              next: () => {
                this.uploading = false;
                this.message = 'Zip upload complete. Job started.';
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
    if (this.selectedSample) {
      this.startSampleUpload();
      return;
    }
    this.error = 'Drop files or select a sample first.';
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
    const items = event.dataTransfer?.items;
    const dropped = items ? await this.readDroppedItems(items) : [];
    const files = dropped.length ? dropped : Array.from(event.dataTransfer?.files || []).map(file => ({
      file,
      relPath: file.name
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
      this.message = `Zip selected: ${files[0].file.name}`;
      return;
    }

    const relPaths = files.map(item => item.relPath);
    const hasFolders = relPaths.some(path => path.includes('/'));
    if (!hasFolders) {
      this.error = 'Please drop folders or a zip file.';
      return;
    }

    const topFolders = Array.from(new Set(relPaths.map(path => path.split('/')[0]).filter(Boolean)));

    if (topFolders.length >= 2) {
      const [aFolder, bFolder] = topFolders;
      this.dropFilesA = files
        .filter(item => item.relPath.startsWith(`${aFolder}/`))
        .map(item => ({ file: item.file, relPath: this.stripPath(item.relPath, 1) }));
      this.dropFilesB = files
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
        this.dropFilesA = files
          .filter(item => item.relPath.includes(`/${aFolder}/`))
          .map(item => ({ file: item.file, relPath: this.stripPath(item.relPath, 2) }));
        this.dropFilesB = files
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
    const parts = path.split('/');
    return parts.slice(segments).join('/') || parts[parts.length - 1];
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

  startSampleUpload() {
    if (!this.selectedSample) return;
    this.message = '';
    this.error = '';
    this.uploading = true;
    this.jobsService.createJob().subscribe({
      next: (job: { id: string }) => {
        this.jobId = job.id;
        this.jobsService.useSample(job.id, this.selectedSample).subscribe({
          next: () => {
            this.jobsService.startJob(job.id).subscribe({
              next: () => {
                this.uploading = false;
                this.message = 'Sample loaded. Job started.';
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
            this.error = this.formatError(err, 'Failed to load sample.');
          }
        });
      },
      error: (err: any) => {
        this.uploading = false;
        this.error = this.formatError(err, 'Failed to create job.');
      }
    });
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
    this.jobsService.listJobs().subscribe((jobs: JobSummary[]) => (this.jobList = jobs));
  }

  loadSamples() {
    this.jobsService.listSamples().subscribe({
      next: samples => {
        this.samples = samples;
      },
      error: () => {
        this.samples = [];
      }
    });
  }

  selectJob(jobId: string) {
    this.jobId = jobId;
    this.loadFiles();
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

  startComparison(jobId: string) {
    this.message = '';
    this.error = '';
    this.jobsService.startJob(jobId).subscribe({
      next: () => {
        this.message = 'Comparison started.';
        this.selectJob(jobId);
        this.loadJobs();
      },
      error: (err: any) => {
        this.error = this.formatError(err, 'Failed to start comparison.');
      }
    });
  }

  clearJobSelection() {
    this.jobId = '';
    this.files = [];
    this.jobProgress = null;
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
}
