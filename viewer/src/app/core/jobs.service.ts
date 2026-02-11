import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface JobFile {
  id: string;
  relative_path: string;
  missing_in_set_a: boolean;
  missing_in_set_b: boolean;
  has_diffs?: boolean;
  text_status?: string | null;
  created_at?: string;
  status?: string;
}

export interface JobSummary {
  id: string;
  display_id: string;
  status: string;
  set_a_label?: string | null;
  set_b_label?: string | null;
  created_at: string;
  files_available?: boolean;
  progress?: JobProgress;
}

export interface JobPage {
  id: string;
  page_index: number;
  status: string;
  diff_score: number | null;
  overlay_svg_path: string | null;
  incompatible_size?: boolean;
  missing_in_set_a?: boolean;
  missing_in_set_b?: boolean;
  error_message?: string | null;
}

export interface SampleSet {
  name: string;
  filesA: string[];
  filesB: string[];
}

export interface JobProgress {
  total: number;
  finished: number;
  percent: number;
  counts: Record<string, number>;
  completed: number;
  missing: number;
  incompatible: number;
  failed: number;
  running: number;
  pending: number;
}

export interface ReportSummary {
  id: string;
  source_job_id: string;
  report_type: 'visual' | 'text' | 'both';
  status: 'queued' | 'running' | 'done' | 'failed';
  progress: number;
  output_filename?: string | null;
  error?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ReportEvent {
  report_id: string;
  source_job_id: string;
  report_type: 'visual' | 'text' | 'both';
  status: 'queued' | 'running' | 'done' | 'failed';
  progress: number;
  output_filename?: string | null;
  error?: string | null;
}

@Injectable({ providedIn: 'root' })
export class JobsService {
  private baseUrl = '/api';

  constructor(private http: HttpClient) {}

  createJob() {
    return this.http.post<{ id: string }>(`${this.baseUrl}/jobs`, {});
  }

  listJobs() {
    return this.http.get<JobSummary[]>(`${this.baseUrl}/jobs`);
  }

  getJob(jobId: string) {
    return this.http.get<JobSummary>(`${this.baseUrl}/jobs/${jobId}`);
  }

  watchJobs(): Observable<JobSummary[]> {
    return new Observable<JobSummary[]>(subscriber => {
      let ws: WebSocket | null = null;
      let closedByUser = false;
      let reconnectTimer: number | null = null;

      const connect = () => {
        const token = localStorage.getItem('access_token');
        if (!token) {
          return;
        }
        const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
        const wsUrl = `${protocol}://${window.location.host}/api/jobs/ws?token=${encodeURIComponent(token)}`;
        ws = new WebSocket(wsUrl);

        ws.onmessage = event => {
          try {
            const data = JSON.parse(event.data) as JobSummary[];
            subscriber.next(data);
          } catch {
            // ignore malformed payloads
          }
        };

        ws.onerror = () => {
          ws?.close();
        };

        ws.onclose = () => {
          if (closedByUser) return;
          reconnectTimer = window.setTimeout(connect, 1500);
        };
      };

      connect();

      return () => {
        closedByUser = true;
        if (reconnectTimer) {
          clearTimeout(reconnectTimer);
        }
        ws?.close();
      };
    });
  }

  listSamples() {
    return this.http.get<SampleSet[]>(`${this.baseUrl}/jobs/samples`);
  }

  useSample(jobId: string, sample: string) {
    return this.http.post(`${this.baseUrl}/jobs/${jobId}/use-sample?sample=${encodeURIComponent(sample)}`, {});
  }

  clearJobs() {
    return this.http.post<{ status: string; deleted: number }>(`${this.baseUrl}/jobs/clear`, {});
  }

  deleteJob(jobId: string) {
    return this.http.delete<{ status: string }>(`${this.baseUrl}/jobs/${jobId}`);
  }

  uploadFolder(jobId: string, setName: 'A' | 'B', files: File[], stripSegments = 1) {
    const form = new FormData();
    files.forEach(file => {
      form.append('files', file);
      const rawPath = (file as any).webkitRelativePath || file.name;
      const parts = rawPath.split('/');
      let relPath = rawPath;
      if (stripSegments > 0 && parts.length > stripSegments) {
        relPath = parts.slice(stripSegments).join('/');
      } else if (parts.length > 1) {
        relPath = parts.slice(1).join('/');
      }
      form.append('relative_paths', relPath || file.name);
    });
    return this.http.post(`${this.baseUrl}/jobs/${jobId}/upload?set=${setName}`, form);
  }

  uploadFolderWithPaths(jobId: string, setName: 'A' | 'B', items: { file: File; relPath: string }[]) {
    const form = new FormData();
    items.forEach(item => {
      form.append('files', item.file);
      form.append('relative_paths', item.relPath || item.file.name);
    });
    return this.http.post(`${this.baseUrl}/jobs/${jobId}/upload?set=${setName}`, form);
  }

  uploadZipSets(jobId: string, zipFile: File) {
    const form = new FormData();
    form.append('zip_file', zipFile);
    return this.http.post(`${this.baseUrl}/jobs/${jobId}/upload-zip`, form);
  }

  startJob(jobId: string, setALabel?: string | null, setBLabel?: string | null) {
    const params: string[] = [];
    if (setALabel) params.push(`setA=${encodeURIComponent(setALabel)}`);
    if (setBLabel) params.push(`setB=${encodeURIComponent(setBLabel)}`);
    const qs = params.length ? `?${params.join('&')}` : '';
    return this.http.post(`${this.baseUrl}/jobs/${jobId}/start${qs}`, {});
  }

  continueJob(jobId: string) {
    return this.http.post(`${this.baseUrl}/jobs/${jobId}/continue`, {});
  }

  listFiles(jobId: string) {
    return this.http.get<JobFile[]>(`${this.baseUrl}/jobs/${jobId}/files`);
  }

  watchJobFiles(jobId: string): Observable<JobFile[]> {
    return new Observable<JobFile[]>(subscriber => {
      let ws: WebSocket | null = null;
      let closedByUser = false;
      let reconnectTimer: number | null = null;

      const connect = () => {
        const token = localStorage.getItem('access_token');
        if (!token) {
          return;
        }
        const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
        const wsUrl = `${protocol}://${window.location.host}/api/jobs/${jobId}/files/ws?token=${encodeURIComponent(token)}`;
        ws = new WebSocket(wsUrl);

        ws.onmessage = event => {
          try {
            const data = JSON.parse(event.data) as JobFile[];
            if (Array.isArray(data)) {
              subscriber.next(data);
            }
          } catch {
            // ignore malformed payloads
          }
        };

        ws.onerror = () => {
          ws?.close();
        };

        ws.onclose = () => {
          if (closedByUser) return;
          reconnectTimer = window.setTimeout(connect, 1500);
        };
      };

      connect();

      return () => {
        closedByUser = true;
        if (reconnectTimer) {
          clearTimeout(reconnectTimer);
        }
        ws?.close();
      };
    });
  }

  getJobProgress(jobId: string) {
    return this.http.get<JobProgress>(`${this.baseUrl}/jobs/${jobId}/progress`);
  }

  listPages(jobId: string, fileId: string) {
    return this.http.get<JobPage[]>(`${this.baseUrl}/jobs/${jobId}/files/${fileId}/pages`);
  }

  getOverlay(jobId: string, fileId: string, pageId: string) {
    return this.http.get(`${this.baseUrl}/jobs/${jobId}/files/${fileId}/pages/${pageId}/overlay`, { responseType: 'text' });
  }

  getFileContent(jobId: string, fileId: string, setName: 'A' | 'B') {
    return `${this.baseUrl}/jobs/${jobId}/files/${fileId}/content?set=${setName}`;
  }

  getFileText(jobId: string, fileId: string, setName: 'A' | 'B') {
    return this.http.get(`${this.baseUrl}/jobs/${jobId}/files/${fileId}/text?set=${setName}`, {
      responseType: 'text'
    });
  }

  createReport(jobId: string, reportType: 'visual' | 'text' | 'both') {
    return this.http.post<ReportSummary>(`${this.baseUrl}/reports`, {
      source_job_id: jobId,
      type: reportType
    });
  }

  listReports(jobId?: string) {
    const params = jobId ? `?source_job_id=${encodeURIComponent(jobId)}` : '';
    return this.http.get<ReportSummary[]>(`${this.baseUrl}/reports${params}`);
  }

  downloadReport(reportId: string) {
    const timestamp = Date.now();
    const params = new URLSearchParams({ t: String(timestamp) });
    return this.http.get(`${this.baseUrl}/reports/${reportId}/download?${params.toString()}`, {
      responseType: 'blob',
      observe: 'response'
    });
  }

  watchReports(): Observable<ReportEvent> {
    return new Observable<ReportEvent>(subscriber => {
      let ws: WebSocket | null = null;
      let closedByUser = false;
      let reconnectTimer: number | null = null;

      const connect = () => {
        const token = localStorage.getItem('access_token');
        if (!token) {
          return;
        }
        const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
        const wsUrl = `${protocol}://${window.location.host}/api/reports/ws?token=${encodeURIComponent(token)}`;
        ws = new WebSocket(wsUrl);

        ws.onmessage = event => {
          try {
            const data = JSON.parse(event.data) as ReportEvent;
            if (data && data.report_id) {
              subscriber.next(data);
            }
          } catch {
            // ignore malformed payloads
          }
        };

        ws.onerror = () => {
          ws?.close();
        };

        ws.onclose = () => {
          if (closedByUser) return;
          reconnectTimer = window.setTimeout(connect, 1500);
        };
      };

      connect();

      return () => {
        closedByUser = true;
        if (reconnectTimer) {
          clearTimeout(reconnectTimer);
        }
        ws?.close();
      };
    });
  }
}
