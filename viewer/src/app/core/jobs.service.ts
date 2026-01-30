import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface JobFile {
  id: string;
  relative_path: string;
  missing_in_set_a: boolean;
  missing_in_set_b: boolean;
}

export interface JobSummary {
  id: string;
  status: string;
  created_at: string;
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

  startJob(jobId: string) {
    return this.http.post(`${this.baseUrl}/jobs/${jobId}/start`, {});
  }

  listFiles(jobId: string) {
    return this.http.get<JobFile[]>(`${this.baseUrl}/jobs/${jobId}/files`);
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
}
