import { AfterViewInit, Component, OnDestroy, OnInit, TemplateRef, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { Subscription } from 'rxjs';
import { JobsService, JobFile, JobSummary } from '../../core/jobs.service';
import { TopbarActionsService } from '../../core/topbar-actions.service';

@Component({
  selector: 'app-jobs',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
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
      <ng-container *ngIf="activeTab === 'dropzone'">
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
                  <button class="btn secondary" (click)="openJobDetails(job.id)">Job Details</button>
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

      <div *ngIf="activeTab === 'jobs'" class="card" style="grid-column: 1 / -1; max-width: 860px; margin: 0 auto;">
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
          style="margin-top: 10px; position: relative; cursor: pointer;"
          [style.border]="job.id === jobId ? '2px solid var(--theme-primary)' : '1px solid transparent'"
          (click)="selectJob(job.id)"
        >
          <div style="display:flex; justify-content: space-between; align-items:flex-start;">
            <div>
              <strong>{{ job.display_id || job.id }}</strong>
              <div style="font-size: 12px; color:#64748b; margin-top: 4px;">
                Set A: {{ job.set_a_label || 'setA' }} · Set B: {{ job.set_b_label || 'setB' }}
              </div>
              <div style="font-size: 12px; color:#94a3b8; margin-top: 4px;">
                Created: {{ formatDate(job.created_at) }}
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
          <div style="position: absolute; top: 12px; right: 12px;">
            <button class="btn secondary" (click)="$event.stopPropagation(); openJobDetails(job.id)">Job Details</button>
          </div>
        </div>
      </div>
    </div>

  `
})
export class JobsComponent implements OnInit, AfterViewInit, OnDestroy {
  @ViewChild('topbarActions', { static: true }) topbarActionsTpl!: TemplateRef<any>;
  activeTab: 'dropzone' | 'jobs' = 'dropzone';
  private jobsSub?: Subscription;
  get selectedJob() {
    return this.jobList.find(job => job.id === this.jobId) || null;
  }
  get recentJobs() {
    return this.jobList.slice(0, 5);
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

  constructor(private jobsService: JobsService, private topbar: TopbarActionsService, private router: Router) {}

  ngOnInit() {
    this.loadJobs();
    this.jobsSub = this.jobsService.watchJobs().subscribe({
      next: jobs => {
        this.jobList = this.sortJobs(jobs);
        this.refreshRecentProgressForMissing();
      }
    });
  }

  setTab(tab: 'dropzone' | 'jobs') {
    this.activeTab = tab;
  }

  ngAfterViewInit() {
    this.topbar.setActions(this.topbarActionsTpl);
  }

  ngOnDestroy() {
    this.jobsSub?.unsubscribe();
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

    const relPaths = files.map(item => item.relPath);
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
        this.setALabel = aFolder;
        this.setBLabel = bFolder;
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
    const parts = path.replace(/\\/g, '/').split('/');
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
