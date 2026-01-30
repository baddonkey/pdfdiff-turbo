import { Component, ElementRef, OnDestroy, OnInit, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { JobsService, JobPage } from '../../core/jobs.service';
import * as pdfjsLib from 'pdfjs-dist';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';

(pdfjsLib as any).GlobalWorkerOptions.workerSrc = '/assets/pdf.worker.min.mjs';

@Component({
  selector: 'app-viewer',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="card">
      <div style="display:flex; justify-content: space-between; align-items:center; margin-bottom: 12px;">
        <div style="display:flex; align-items:center; gap: 12px;">
          <button class="btn secondary" (click)="backToJobs()">Back</button>
          <h2 style="margin:0;">File Viewer</h2>
        </div>
        <div>
          <button class="btn secondary" (click)="prevDiff()">Prev Diff</button>
          <button class="btn" (click)="nextDiff()">Next Diff</button>
        </div>
      </div>

      <div *ngIf="loadError" style="margin-bottom: 12px; color: #c62828;">
        {{ loadError }}
      </div>

      <div class="viewer-grid" *ngIf="!loadError">
        <div class="canvas-wrap">
          <div class="page-size">{{ pageSizeLabel }}</div>
          <canvas #canvasA></canvas>
          <div class="overlay overlay-left" [style.width.px]="overlayWidth" [style.height.px]="overlayHeight" [innerHTML]="overlaySvgLeft"></div>
        </div>
        <div class="canvas-wrap">
          <div class="page-size">{{ pageSizeLabel }}</div>
          <canvas #canvasB></canvas>
          <div class="overlay overlay-right" [style.width.px]="overlayWidth" [style.height.px]="overlayHeight" [innerHTML]="overlaySvgRight"></div>
        </div>
      </div>

      <div style="margin-top: 16px; display:flex; gap: 12px; align-items:center;">
        <button class="btn secondary" (click)="prevPage()">Prev Page</button>
        <div>Page {{ currentPage + 1 }} / {{ totalPages }}</div>
        <button class="btn" (click)="nextPage()">Next Page</button>
      </div>
    </div>
  `
})
export class ViewerComponent implements OnInit, OnDestroy {
  @ViewChild('canvasA', { static: false }) canvasA?: ElementRef<HTMLCanvasElement>;
  @ViewChild('canvasB', { static: false }) canvasB?: ElementRef<HTMLCanvasElement>;

  jobId = '';
  fileId = '';
  pages: JobPage[] = [];
  currentPage = 0;
  totalPages = 0;
  overlaySvgLeft: SafeHtml = '';
  overlaySvgRight: SafeHtml = '';
  overlayWidth = 0;
  overlayHeight = 0;
  loadError = '';
  pageSizeLabel = '';

  private pdfA: any;
  private pdfB: any;

  constructor(
    private route: ActivatedRoute,
    private jobs: JobsService,
    private router: Router,
    private sanitizer: DomSanitizer
  ) {}

  ngOnInit(): void {
    this.jobId = this.route.snapshot.paramMap.get('jobId') || '';
    this.fileId = this.route.snapshot.paramMap.get('fileId') || '';
    this.jobs.listPages(this.jobId, this.fileId).subscribe({
      next: pages => {
        this.pages = pages.sort((a, b) => a.page_index - b.page_index);
        this.totalPages = this.pages.length;
        if (!this.totalPages) {
          this.loadError = 'No pages found for this file.';
          return;
        }
        this.loadPdfPair();
      },
      error: () => {
        this.loadError = 'Failed to load pages for this file.';
      }
    });
  }

  ngOnDestroy(): void {
    this.pdfA?.destroy?.();
    this.pdfB?.destroy?.();
  }

  async loadPdfPair() {
    const fileInfo = this.pages[0];
    if (!fileInfo) return;

    const setAUrl = this.jobs.getFileContent(this.jobId, this.fileId, 'A');
    const setBUrl = this.jobs.getFileContent(this.jobId, this.fileId, 'B');

    const token = localStorage.getItem('access_token') || '';
    const headers = token ? { Authorization: `Bearer ${token}` } : undefined;
    try {
      this.pdfA = await (pdfjsLib as any).getDocument({
        url: setAUrl,
        httpHeaders: headers,
        disableWorker: true
      }).promise;
      this.pdfB = await (pdfjsLib as any).getDocument({
        url: setBUrl,
        httpHeaders: headers,
        disableWorker: true
      }).promise;
      await this.renderPage();
    } catch (err) {
      console.error('PDF load error', err);
      this.loadError = 'Failed to load PDFs. Please sign in again and retry.';
    }
  }

  async renderPage() {
    const page = this.pages[this.currentPage];
    if (!page) return;
    if (!this.canvasA?.nativeElement || !this.canvasB?.nativeElement) return;

    try {
      if (page.missing_in_set_a) {
        this.clearCanvas(this.canvasA.nativeElement);
      } else {
        await this.renderPdfPage(this.pdfA, this.currentPage + 1, this.canvasA.nativeElement);
      }

      if (page.missing_in_set_b) {
        this.clearCanvas(this.canvasB.nativeElement);
      } else {
        await this.renderPdfPage(this.pdfB, this.currentPage + 1, this.canvasB.nativeElement);
      }

      this.overlayWidth = this.canvasA.nativeElement.width;
      this.overlayHeight = this.canvasA.nativeElement.height;
    } catch (err) {
      console.error('PDF render error', err);
      this.loadError = 'Failed to render PDF pages.';
      return;
    }

    this.overlaySvgLeft = '';
    this.overlaySvgRight = '';
    if (page.status === 'done') {
      this.jobs.getOverlay(this.jobId, this.fileId, String(page.page_index)).subscribe({
        next: svg => {
          const safe = this.sanitizer.bypassSecurityTrustHtml(svg);
          this.overlaySvgLeft = safe;
          this.overlaySvgRight = safe;
        },
        error: () => {
          this.overlaySvgLeft = '';
          this.overlaySvgRight = '';
        }
      });
    }
  }

  async renderPdfPage(pdf: any, pageNumber: number, canvas: HTMLCanvasElement) {
    if (!pdf) throw new Error('PDF not loaded');
    if (pdf.numPages && pageNumber > pdf.numPages) {
      this.clearCanvas(canvas);
      return;
    }
    const page = await pdf.getPage(pageNumber);
    const viewport1 = page.getViewport({ scale: 1 });
    const viewport = page.getViewport({ scale: 1.2 });
    const context = canvas.getContext('2d');
    if (!context) throw new Error('Canvas context missing');
    canvas.height = viewport.height;
    canvas.width = viewport.width;
    const widthMm = (viewport1.width * 25.4) / 72;
    const heightMm = (viewport1.height * 25.4) / 72;
    this.pageSizeLabel = `${widthMm.toFixed(0)} × ${heightMm.toFixed(0)} mm`;
    await page.render({ canvasContext: context, viewport }).promise;
  }

  private clearCanvas(canvas: HTMLCanvasElement) {
    const context = canvas.getContext('2d');
    if (!context) return;
    context.clearRect(0, 0, canvas.width, canvas.height);
  }

  prevPage() {
    if (this.currentPage > 0) {
      this.currentPage--;
      this.renderPage();
    }
  }

  nextPage() {
    if (this.currentPage < this.totalPages - 1) {
      this.currentPage++;
      this.renderPage();
    }
  }

  nextDiff() {
    const idx = this.pages.findIndex((p, i) => i > this.currentPage && (p.diff_score || 0) > 0);
    if (idx >= 0) {
      this.currentPage = idx;
      this.renderPage();
    }
  }

  prevDiff() {
    for (let i = this.currentPage - 1; i >= 0; i--) {
      if ((this.pages[i].diff_score || 0) > 0) {
        this.currentPage = i;
        this.renderPage();
        break;
      }
    }
  }

  backToJobs() {
    this.router.navigate(['/jobs']);
  }
}
