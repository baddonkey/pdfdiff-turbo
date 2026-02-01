import { Component, ElementRef, HostListener, OnDestroy, OnInit, ViewChild, Renderer2, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { JobsService, JobFile, JobPage, JobSummary } from '../../core/jobs.service';
import { TopbarActionsService } from '../../core/topbar-actions.service';
import * as pdfjsLib from 'pdfjs-dist';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';

(pdfjsLib as any).GlobalWorkerOptions.workerSrc = '/assets/pdf.worker.min.mjs';

@Component({
  selector: 'app-viewer',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="card">
      <div class="viewer-header" style="display:flex; justify-content: space-between; align-items:center; margin-bottom: 12px;">
        <div style="display:flex; align-items:center; gap: 12px;">
          <button class="btn secondary" (click)="backToJobs()">Back</button>
          <h2 style="margin:0;" *ngIf="!currentFile">File Viewer</h2>
          <h2 style="margin:0;" *ngIf="currentFile">{{ currentFile.relative_path }}</h2>
        </div>
        <div style="display:flex; align-items:center; gap: 8px;">
          <button class="btn secondary" [class.magnifier-active]="magnifierEnabled" (click)="toggleMagnifier()" style="display: flex; align-items: center; gap: 6px;">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="11" cy="11" r="8"></circle>
              <path d="m21 21-4.35-4.35"></path>
            </svg>
            Magnifier
          </button>
          <button class="btn secondary" (click)="prevDiff()">Prev Diff</button>
          <button class="btn" (click)="nextDiff()">Next Diff</button>
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
                <th style="padding: 6px 4px;">Diff</th>
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
                  <span class="badge" [ngClass]="file.has_diffs ? 'warn' : 'neutral'">
                    {{ file.has_diffs ? 'Diff' : 'No Diff' }}
                  </span>
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
          <div class="viewer-grid">
            <div
              class="canvas-wrap"
              data-side="A"
              [class.magnifier-on]="magnifierEnabled"
              (mouseenter)="onMagnifierEnter($event, 'A')"
              (mousemove)="onMagnifierMove($event, 'A')"
              (mouseleave)="hideMagnifier('A')"
            >
              <div class="page-size">{{ job?.set_a_label || 'Set A' }} - {{ pageSizeLabel }}</div>
              <canvas #canvasA></canvas>
              <div class="overlay overlay-left" [style.width.px]="overlayWidth" [style.height.px]="overlayHeight" [innerHTML]="overlaySvgLeft"></div>
            </div>
            <div
              class="canvas-wrap"
              data-side="B"
              [class.magnifier-on]="magnifierEnabled"
              (mouseenter)="onMagnifierEnter($event, 'B')"
              (mousemove)="onMagnifierMove($event, 'B')"
              (mouseleave)="hideMagnifier('B')"
            >
              <div class="page-size">{{ job?.set_b_label || 'Set B' }} - {{ pageSizeLabel }}</div>
              <canvas #canvasB></canvas>
              <div class="overlay overlay-right" [style.width.px]="overlayWidth" [style.height.px]="overlayHeight" [innerHTML]="overlaySvgRight"></div>
            </div>
          </div>

          <div class="viewer-pager" style="margin-top: 16px; display:flex; gap: 12px; align-items:center;">
            <button class="btn secondary" (click)="prevPage()">Prev Page</button>
            <div>Page {{ currentPage + 1 }} / {{ totalPages }}</div>
            <button class="btn" (click)="nextPage()">Next Page</button>
          </div>
        </div>
      </div>
      
      <!-- Magnifiers at document level for proper z-index -->
      <div
        #magnifierWrapA
        class="magnifier"
        [style.width.px]="magnifierSize"
        [style.height.px]="magnifierSize"
      >
        <canvas #magnifierA></canvas>
      </div>
      <div
        #magnifierWrapB
        class="magnifier"
        [style.width.px]="magnifierSize"
        [style.height.px]="magnifierSize"
      >
        <canvas #magnifierB></canvas>
      </div>
    </div>
  `
})
export class ViewerComponent implements OnInit, OnDestroy {
  @ViewChild('canvasA', { static: false }) canvasA?: ElementRef<HTMLCanvasElement>;
  @ViewChild('canvasB', { static: false }) canvasB?: ElementRef<HTMLCanvasElement>;
  @ViewChild('magnifierA', { static: false }) magnifierCanvasA?: ElementRef<HTMLCanvasElement>;
  @ViewChild('magnifierB', { static: false }) magnifierCanvasB?: ElementRef<HTMLCanvasElement>;
  @ViewChild('magnifierWrapA', { static: false }) magnifierWrapA?: ElementRef<HTMLDivElement>;
  @ViewChild('magnifierWrapB', { static: false }) magnifierWrapB?: ElementRef<HTMLDivElement>;

  jobId = '';
  fileId = '';
  job: JobSummary | null = null;
  files: JobFile[] = [];
  private filesWs?: { unsubscribe: () => void };
  pages: JobPage[] = [];
  currentPage = 0;
  totalPages = 0;
  overlaySvgLeft: SafeHtml = '';
  overlaySvgRight: SafeHtml = '';
  overlayWidth = 0;
  overlayHeight = 0;
  overlayRenderWidth = 0;
  overlayRenderHeight = 0;
  loadError = '';
  pageSizeLabel = '';

  magnifierEnabled = false;
  magnifierSize = 160;
  magnifierZoom = 2.5;
  renderQuality = 2;

  private overlaySvgRaw = '';
  private overlayImage?: HTMLImageElement;
  private overlayImageUrl?: string;
  private overlayImageReady = false;

  private pdfA: any;
  private pdfB: any;

  constructor(
    private route: ActivatedRoute,
    private jobs: JobsService,
    private router: Router,
    private sanitizer: DomSanitizer,
    private renderer: Renderer2,
    private cdr: ChangeDetectorRef,
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
      
      // Defer to avoid ExpressionChangedAfterItHasBeenCheckedError
      setTimeout(() => {
        if (jobChanged) {
          this.loadJob();
          this.loadJobFiles();
          this.subscribeJobFiles();
        }
        if (fileChanged) {
          this.loadFilePages();
        }
      }, 0);
    });
  }

  @HostListener('window:resize')
  onWindowResize() {
    // Re-render PDFs when window is resized to recalculate scale
    if (this.pdfA && this.pdfB) {
      this.renderPage();
    }
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

  loadFilePages() {
    if (!this.jobId || !this.fileId) return;
    this.loadError = '';
    this.pages = [];
    this.currentPage = 0;
    this.totalPages = 0;
    this.resetPdfs();
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

  openFile(file: JobFile) {
    if (!file?.id) return;
    this.router.navigate(['/jobs', this.jobId, 'files', file.id]);
  }

  fileStatusBadge(file: JobFile) {
    const status = (file.status || (file.missing_in_set_a || file.missing_in_set_b ? 'missing' : 'ready')).toLowerCase();
    if (status === 'running' || status === 'pending') return 'badge warn';
    if (status === 'failed' || status === 'incompatible') return 'badge danger';
    if (status === 'missing') return 'badge warn';
    if (status === 'completed') return 'badge success';
    return 'badge neutral';
  }


  ngOnDestroy(): void {
    this.resetPdfs();
    this.filesWs?.unsubscribe();
    this.topbar.setJobTitle(null);
  }

  private resetPdfs() {
    this.pdfA?.destroy?.();
    this.pdfB?.destroy?.();
    this.pdfA = null;
    this.pdfB = null;
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

      this.overlayWidth = this.canvasA.nativeElement.clientWidth || this.canvasA.nativeElement.width;
      this.overlayHeight = this.canvasA.nativeElement.clientHeight || this.canvasA.nativeElement.height;
      this.overlayRenderWidth = this.canvasA.nativeElement.width;
      this.overlayRenderHeight = this.canvasA.nativeElement.height;
    } catch (err) {
      console.error('PDF render error', err);
      this.loadError = 'Failed to render PDF pages.';
      return;
    }

    this.overlaySvgLeft = '';
    this.overlaySvgRight = '';
    this.overlaySvgRaw = '';
    this.overlayImage = undefined;
    this.overlayImageReady = false;
    if (this.overlayImageUrl) {
      URL.revokeObjectURL(this.overlayImageUrl);
      this.overlayImageUrl = undefined;
    }
    if (page.status === 'done') {
      this.jobs.getOverlay(this.jobId, this.fileId, String(page.page_index)).subscribe({
        next: svg => {
          this.overlaySvgRaw = svg;
          this.overlayImage = this.buildOverlayImage(svg);
          const safe = this.sanitizer.bypassSecurityTrustHtml(svg);
          this.overlaySvgLeft = safe;
          this.overlaySvgRight = safe;
        },
        error: () => {
          this.overlaySvgLeft = '';
          this.overlaySvgRight = '';
          this.overlaySvgRaw = '';
          this.overlayImage = undefined;
          this.overlayImageReady = false;
          if (this.overlayImageUrl) {
            URL.revokeObjectURL(this.overlayImageUrl);
            this.overlayImageUrl = undefined;
          }
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

    const viewportHeight = window.visualViewport?.height ?? window.innerHeight;
    const topbarHeight = (document.querySelector('.topbar') as HTMLElement | null)?.clientHeight ?? 0;
    const headerHeight = (document.querySelector('.viewer-header') as HTMLElement | null)?.clientHeight ?? 0;
    const pagerHeight = (document.querySelector('.viewer-pager') as HTMLElement | null)?.clientHeight ?? 0;
    const containerPadding = 48; // 24px top + 24px bottom
    const cardPadding = 40; // 20px top + 20px bottom
    const sectionGaps = 32; // header margin + pager margin + minor gaps

    const reservedHeight = topbarHeight + headerHeight + pagerHeight + containerPadding + cardPadding + sectionGaps;
    const availableHeight = Math.max(viewportHeight - reservedHeight, 200);
    const scaleToFitHeight = availableHeight / viewport1.height;

    const wrap = canvas.closest('.canvas-wrap') as HTMLElement | null;
    let availableWidthPerCanvas = 0;
    if (wrap) {
      const styles = window.getComputedStyle(wrap);
      const paddingX = (parseFloat(styles.paddingLeft) || 0) + (parseFloat(styles.paddingRight) || 0);
      availableWidthPerCanvas = Math.max(wrap.clientWidth - paddingX, 120);
    } else {
      const reservedWidth = 480;
      availableWidthPerCanvas = Math.max((window.innerWidth - reservedWidth) / 2, 120);
    }

    const scaleToFitWidth = availableWidthPerCanvas / viewport1.width;
    
    // Use the smaller of the two scales to ensure it fits in both dimensions
    const scaleToFit = Math.min(scaleToFitHeight, scaleToFitWidth);
    const finalScale = Math.min(Math.max(scaleToFit, 0.5), 3); // clamp between 0.5 and 3
    
    const displayViewport = page.getViewport({ scale: finalScale });
    const renderScale = finalScale * this.renderQuality;
    const viewport = page.getViewport({ scale: renderScale });
    const context = canvas.getContext('2d');
    if (!context) throw new Error('Canvas context missing');
    canvas.height = viewport.height;
    canvas.width = viewport.width;
    canvas.style.width = `${displayViewport.width}px`;
    canvas.style.height = `${displayViewport.height}px`;
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

  toggleMagnifier() {
    this.magnifierEnabled = !this.magnifierEnabled;
    if (!this.magnifierEnabled) {
      this.hideMagnifier('A');
      this.hideMagnifier('B');
    }
  }

  hideMagnifier(side: 'A' | 'B') {
    // Hide both magnifiers when leaving either canvas
    const elA = this.magnifierWrapA?.nativeElement;
    const elB = this.magnifierWrapB?.nativeElement;
    if (elA) {
      elA.style.display = 'none';
    }
    if (elB) {
      elB.style.display = 'none';
    }
  }

  onMagnifierEnter(event: MouseEvent, side: 'A' | 'B') {
    if (!this.magnifierEnabled) return;
    const el = side === 'A' ? this.magnifierWrapA?.nativeElement : this.magnifierWrapB?.nativeElement;
    if (el) {
      el.style.display = 'block';
    }
    this.onMagnifierMove(event, side);
  }

  onMagnifierMove(event: MouseEvent, side: 'A' | 'B', wrapOverride?: HTMLElement) {
    if (!this.magnifierEnabled) return;
    const current = event.currentTarget as HTMLElement | null;
    const wrap = wrapOverride
      ?? (current && !(current instanceof HTMLCanvasElement) ? current : null)
      ?? (event.target as HTMLElement | null)?.closest?.('.canvas-wrap')
      ?? null;
    const canvasFromWrap = wrap ? (wrap.querySelector('canvas') as HTMLCanvasElement | null) : null;
    const canvas = (current instanceof HTMLCanvasElement ? current : null)
      ?? canvasFromWrap
      ?? (side === 'A' ? this.canvasA?.nativeElement : this.canvasB?.nativeElement);
    const magCanvas = side === 'A' ? this.magnifierCanvasA?.nativeElement : this.magnifierCanvasB?.nativeElement;
    if (!canvas || !magCanvas) return;
    const canvasRect = canvas.getBoundingClientRect();
    const localX = event.clientX - canvasRect.left;
    const localY = event.clientY - canvasRect.top;
    if (localX < 0 || localY < 0 || localX > canvasRect.width || localY > canvasRect.height) {
      this.hideMagnifier(side);
      return;
    }

    const scaleX = canvas.width / canvasRect.width;
    const scaleY = canvas.height / canvasRect.height;
    const normX = localX / canvasRect.width;
    const normY = localY / canvasRect.height;
    const cx = normX * canvas.width;
    const cy = normY * canvas.height;
    this.renderMagnifier(side, canvas, magCanvas, canvasRect, cx, cy, event.clientX, event.clientY);

    const otherSide = side === 'A' ? 'B' : 'A';
    const otherCanvas = otherSide === 'A' ? this.canvasA?.nativeElement : this.canvasB?.nativeElement;
    const otherMagCanvas = otherSide === 'A' ? this.magnifierCanvasA?.nativeElement : this.magnifierCanvasB?.nativeElement;
    if (otherCanvas && otherMagCanvas) {
      const otherRect = otherCanvas.getBoundingClientRect();
      const otherCx = normX * otherCanvas.width;
      const otherCy = normY * otherCanvas.height;
      const otherClientX = otherRect.left + normX * otherRect.width;
      const otherClientY = otherRect.top + normY * otherRect.height;
      this.renderMagnifier(otherSide, otherCanvas, otherMagCanvas, otherRect, otherCx, otherCy, otherClientX, otherClientY);
    }
  }

  @HostListener('document:mousemove', ['$event'])
  onDocumentMouseMove(event: MouseEvent) {
    if (!this.magnifierEnabled) return;
    const canvasA = this.canvasA?.nativeElement;
    const canvasB = this.canvasB?.nativeElement;
    if (!canvasA && !canvasB) return;
    const rectA = canvasA?.getBoundingClientRect();
    const rectB = canvasB?.getBoundingClientRect();
    const x = event.clientX;
    const y = event.clientY;
    const inA = !!rectA && x >= rectA.left && x <= rectA.right && y >= rectA.top && y <= rectA.bottom;
    const inB = !!rectB && x >= rectB.left && x <= rectB.right && y >= rectB.top && y <= rectB.bottom;
    if (inA) {
      this.onMagnifierMove(event, 'A', canvasA?.parentElement || undefined);
    } else if (inB) {
      this.onMagnifierMove(event, 'B', canvasB?.parentElement || undefined);
    }
  }



  private renderMagnifier(
    side: 'A' | 'B',
    canvas: HTMLCanvasElement,
    magCanvas: HTMLCanvasElement,
    canvasRect: DOMRect,
    cx: number,
    cy: number,
    clientX: number,
    clientY: number
  ) {
    const size = this.magnifierSize;
    const radius = size / 2;
    magCanvas.width = size;
    magCanvas.height = size;
    const ctx = magCanvas.getContext('2d');
    if (!ctx) return;
    ctx.clearRect(0, 0, size, size);
    ctx.save();
    ctx.beginPath();
    ctx.arc(radius, radius, radius - 2, 0, Math.PI * 2);
    ctx.clip();
    try {
      const zoom = this.magnifierZoom;
      ctx.setTransform(zoom, 0, 0, zoom, radius - cx * zoom, radius - cy * zoom);
      ctx.drawImage(canvas, 0, 0);
      if (this.overlayImage && this.overlayImageReady) {
        try {
          const zoom = this.magnifierZoom;
          ctx.setTransform(zoom, 0, 0, zoom, radius - cx * zoom, radius - cy * zoom);
          ctx.drawImage(this.overlayImage, 0, 0, canvas.width, canvas.height);
          ctx.setTransform(1, 0, 0, 1, 0, 0);
        } catch (err) {
          ctx.setTransform(1, 0, 0, 1, 0, 0);
        }
      }
      ctx.setTransform(1, 0, 0, 1, 0, 0);
    } catch (err) {
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.fillStyle = '#ffffff';
      ctx.fillRect(0, 0, size, size);
      ctx.strokeStyle = '#cbd5f5';
      ctx.lineWidth = 1;
      for (let i = 0; i <= size; i += 12) {
        ctx.beginPath();
        ctx.moveTo(i, 0);
        ctx.lineTo(i, size);
        ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(0, i);
        ctx.lineTo(size, i);
        ctx.stroke();
      }
    }
    ctx.restore();
    ctx.beginPath();
    ctx.arc(radius, radius, radius - 1, 0, Math.PI * 2);
    ctx.strokeStyle = 'rgba(15, 23, 42, 0.45)';
    ctx.lineWidth = 2;
    ctx.stroke();

    // Position magnifier circle offset from cursor (bottom-right)
    const offsetX = 20;
    const offsetY = 20;
    const left = clientX + offsetX;
    const top = clientY + offsetY;
    this.positionMagnifier(side, left, top);
  }

  private buildOverlayImage(svg: string) {
    if (!svg) return undefined;
    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.onload = () => {
      this.overlayImageReady = true;
      if (this.overlayRenderWidth && this.overlayRenderHeight) {
        img.width = this.overlayRenderWidth;
        img.height = this.overlayRenderHeight;
      }
    };
    img.onerror = () => {
      this.overlayImage = undefined;
      this.overlayImageReady = false;
    };
    const width = this.overlayRenderWidth || undefined;
    const height = this.overlayRenderHeight || undefined;
    let svgText = svg.replace(/<\?xml[^>]*\?>/g, '');
    svgText = svgText.replace(/currentColor/g, '#ff0000');
    svgText = svgText.replace(/stroke:#ff0000/g, 'stroke:#ff0000');
    svgText = svgText.replace(/stroke="currentColor"/g, 'stroke="#ff0000"');
    svgText = svgText.replace(/stroke='currentColor'/g, "stroke='#ff0000'");
    if (!/width=/.test(svgText) && width) {
      svgText = svgText.replace('<svg', `<svg width="${width}"`);
    }
    if (!/height=/.test(svgText) && height) {
      svgText = svgText.replace('<svg', `<svg height="${height}"`);
    }
    if (!/style=/.test(svgText)) {
      svgText = svgText.replace('<svg', `<svg style="color:#ff0000; stroke:#ff0000; fill:none;"`);
    }
    if (this.overlayImageUrl) {
      URL.revokeObjectURL(this.overlayImageUrl);
    }
    const blob = new Blob([svgText], { type: 'image/svg+xml' });
    this.overlayImageUrl = URL.createObjectURL(blob);
    img.src = this.overlayImageUrl;
    return img;
  }

  private clamp(value: number, min: number, max: number) {
    return Math.max(min, Math.min(max, value));
  }

  private positionMagnifier(side: 'A' | 'B', left: number, top: number) {
    const el = side === 'A' ? this.magnifierWrapA?.nativeElement : this.magnifierWrapB?.nativeElement;
    if (!el) {
      console.error('Magnifier element not found for side:', side);
      return;
    }
    
    // Use Renderer2 for reliable DOM manipulation
    this.renderer.setStyle(el, 'display', 'block');
    this.renderer.setStyle(el, 'position', 'fixed');
    this.renderer.setStyle(el, 'left', `${left}px`);
    this.renderer.setStyle(el, 'top', `${top}px`);
    this.renderer.setStyle(el, 'pointer-events', 'none');
    this.renderer.setStyle(el, 'z-index', '99999');
    this.renderer.setStyle(el, 'transform', 'translate(0, 0)');
  }
}
