import io
import re
import shutil
import zipfile
import json
from pathlib import Path, PurePosixPath
from typing import Iterable
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.celery_app import celery_app
from app.features.jobs.models import Job, JobFile, JobPageResult, JobStatus, PageStatus
from app.features.jobs.repository import JobFileRepository, JobPageResultRepository, JobRepository
from app.features.jobs.schemas import (
    JobCreatedMessage,
    JobFileMessage,
    JobPageMessage,
    JobStartedMessage,
    JobStatusMessage,
    JobSummaryMessage,
)
from app.features.jobs.storage import ensure_relative_path, list_relative_files, write_bytes


class JobService:
    def __init__(
        self,
        session: AsyncSession,
        job_repo: JobRepository,
        file_repo: JobFileRepository,
        page_repo: JobPageResultRepository,
    ):
        self._session = session
        self._job_repo = job_repo
        self._file_repo = file_repo
        self._page_repo = page_repo

    async def create_job(self, user_id: str) -> JobCreatedMessage:
        job = Job(user_id=user_id)
        self._job_repo.add(job)
        await self._session.commit()
        await self._session.refresh(job)
        return JobCreatedMessage(
            id=str(job.id),
            display_id=self._display_id(job),
            status=job.status.value,
            set_a_label=job.set_a_label,
            set_b_label=job.set_b_label,
            has_diffs=job.has_diffs,
            created_at=job.created_at,
        )

    async def upload_zip(self, job: Job, set_name: str, zip_bytes: bytes) -> None:
        target_dir = self._job_dir(str(job.id), set_name)
        target_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            for info in zf.infolist():
                if info.is_dir():
                    continue
                rel = ensure_relative_path(info.filename)
                data = zf.read(info)
                write_bytes(target_dir, rel, data)

    async def upload_zip_sets(self, job: Job, zip_bytes: bytes) -> None:
        target_a = self._job_dir(str(job.id), "setA")
        target_b = self._job_dir(str(job.id), "setB")
        target_a.mkdir(parents=True, exist_ok=True)
        target_b.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            top_folders = sorted(
                {
                    PurePosixPath(info.filename).parts[0]
                    for info in zf.infolist()
                    if not info.is_dir() and PurePosixPath(info.filename).parts
                }
            )

            if len(top_folders) < 2:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Zip must contain at least two top-level folders",
                )

            folder_a, folder_b = top_folders[0], top_folders[1]
            job.set_a_label = folder_a
            job.set_b_label = folder_b
            count_a = 0
            count_b = 0

            for info in zf.infolist():
                if info.is_dir():
                    continue
                posix_path = PurePosixPath(info.filename)
                if not posix_path.parts:
                    continue
                top = posix_path.parts[0]
                rel_parts = posix_path.parts[1:]
                if not rel_parts:
                    continue
                rel = ensure_relative_path(str(PurePosixPath(*rel_parts)))
                data = zf.read(info)

                if top == folder_a:
                    write_bytes(target_a, rel, data)
                    count_a += 1
                elif top == folder_b:
                    write_bytes(target_b, rel, data)
                    count_b += 1

            if count_a == 0 or count_b == 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Zip must include files in two top-level folders",
                )
        await self._session.commit()

    async def upload_multipart(self, job: Job, set_name: str, files: Iterable[tuple[str, bytes]]) -> None:
        target_dir = self._job_dir(str(job.id), set_name)
        target_dir.mkdir(parents=True, exist_ok=True)
        for rel, data in files:
            rel_path = ensure_relative_path(rel)
            write_bytes(target_dir, rel_path, data)

    async def start_job(self, job: Job) -> JobStartedMessage:
        set_a_dir = self._job_dir(str(job.id), "setA")
        set_b_dir = self._job_dir(str(job.id), "setB")
        set_a = list_relative_files(set_a_dir)
        set_b = list_relative_files(set_b_dir)

        await self._file_repo.delete_for_job(job.id)
        job.has_diffs = False

        pairs = self._pair_paths(set_a, set_b)
        files = [
            JobFile(
                job_id=job.id,
                relative_path=pair["relative_path"],
                set_a_path=pair["set_a_path"],
                set_b_path=pair["set_b_path"],
                missing_in_set_a=pair["missing_in_set_a"],
                missing_in_set_b=pair["missing_in_set_b"],
                has_diffs=False,
            )
            for pair in pairs
        ]
        self._file_repo.add_many(files)

        job.status = JobStatus.running
        await self._session.commit()
        celery_app.send_task("run_job", args=[str(job.id)])
        return JobStartedMessage(id=str(job.id), status=job.status.value)

    async def continue_job(self, job: Job) -> JobStartedMessage:
        if job.status == JobStatus.cancelled:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Job is cancelled")

        result = await self._session.execute(
            select(JobPageResult)
            .join(JobFile, JobPageResult.job_file_id == JobFile.id)
            .where(JobFile.job_id == job.id)
            .where(JobPageResult.status.in_([PageStatus.pending, PageStatus.failed]))
        )
        pages = list(result.scalars().all())
        if not pages:
            return JobStartedMessage(id=str(job.id), status=job.status.value)

        for page in pages:
            if page.status == PageStatus.failed:
                page.status = PageStatus.pending
                page.diff_score = None
                page.incompatible_size = False
                page.overlay_svg_path = None
                page.error_message = None
            page.task_id = None

        await self._session.commit()

        for page in pages:
            if page.status == PageStatus.pending:
                async_result = celery_app.send_task("compare_page", args=[str(page.id)])
                page.task_id = async_result.id

        job.status = JobStatus.running
        await self._session.commit()
        return JobStartedMessage(id=str(job.id), status=job.status.value)

    async def list_files(self, job: Job) -> list[JobFileMessage]:
        items = await self._file_repo.list_for_job(job.id)
        return [
            JobFileMessage(
                id=str(item.id),
                relative_path=item.relative_path,
                set_a_path=item.set_a_path,
                set_b_path=item.set_b_path,
                missing_in_set_a=item.missing_in_set_a,
                missing_in_set_b=item.missing_in_set_b,
                has_diffs=item.has_diffs,
                status="missing" if (item.missing_in_set_a or item.missing_in_set_b) else "ready",
                created_at=item.created_at,
            )
            for item in items
        ]

    async def list_pages(self, file_id: str) -> list[JobPageMessage]:
        pages = await self._page_repo.list_for_file(file_id)
        return [
            JobPageMessage(
                id=str(page.id),
                page_index=page.page_index,
                status=page.status.value,
                diff_score=page.diff_score,
                incompatible_size=page.incompatible_size,
                missing_in_set_a=page.missing_in_set_a,
                missing_in_set_b=page.missing_in_set_b,
                overlay_svg_path=page.overlay_svg_path,
                error_message=page.error_message,
                created_at=page.created_at,
            )
            for page in pages
        ]

    async def get_status(self, job: Job) -> JobStatusMessage:
        return JobStatusMessage(
            id=str(job.id),
            display_id=self._display_id(job),
            status=job.status.value,
            set_a_label=job.set_a_label,
            set_b_label=job.set_b_label,
            has_diffs=job.has_diffs,
            created_at=job.created_at,
        )

    async def list_jobs(self, user_id: str) -> list[JobSummaryMessage]:
        jobs = await self._job_repo.list_for_user(user_id)
        return [
            JobSummaryMessage(
                id=str(job.id),
                display_id=self._display_id(job),
                status=job.status.value,
                set_a_label=job.set_a_label,
                set_b_label=job.set_b_label,
                has_diffs=job.has_diffs,
                created_at=job.created_at,
            )
            for job in jobs
        ]

    async def clear_jobs(self, user_id: str) -> dict:
        jobs = await self._job_repo.list_for_user(user_id)
        for job in jobs:
            await self._page_repo.delete_for_job(job.id)
            await self._file_repo.delete_for_job(job.id)
            job_dir = Path(settings.data_dir) / "jobs" / str(job.id)
            shutil.rmtree(job_dir, ignore_errors=True)
        await self._job_repo.delete_for_user(user_id)
        await self._session.commit()
        return {"status": "ok", "deleted": len(jobs)}

    async def delete_job(self, job: Job) -> dict:
        await self._page_repo.delete_for_job(job.id)
        await self._file_repo.delete_for_job(job.id)
        job_dir = Path(settings.data_dir) / "jobs" / str(job.id)
        shutil.rmtree(job_dir, ignore_errors=True)
        await self._job_repo.delete_for_job(str(job.id), str(job.user_id))
        await self._session.commit()
        return {"status": "ok"}

    def list_samples(self) -> list[dict]:
        samples_dir = Path(settings.data_dir) / "samples"
        if not samples_dir.exists():
            return []
        samples: list[dict] = []
        for item in sorted(samples_dir.iterdir()):
            if not item.is_dir():
                continue
            set_a = item / "A"
            set_b = item / "B"
            if not set_a.exists() or not set_b.exists():
                continue
            samples.append(
                {
                    "name": item.name,
                    "filesA": sorted([str(p.relative_to(set_a)).replace('\\', '/') for p in set_a.rglob('*') if p.is_file()]),
                    "filesB": sorted([str(p.relative_to(set_b)).replace('\\', '/') for p in set_b.rglob('*') if p.is_file()]),
                }
            )
        return samples

    async def use_sample(self, job: Job, sample_name: str) -> dict:
        samples_dir = Path(settings.data_dir) / "samples"
        source = samples_dir / sample_name
        set_a = source / "A"
        set_b = source / "B"
        if not set_a.exists() or not set_b.exists():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sample not found")

        target_a = self._job_dir(str(job.id), "setA")
        target_b = self._job_dir(str(job.id), "setB")
        target_a.mkdir(parents=True, exist_ok=True)
        target_b.mkdir(parents=True, exist_ok=True)

        for src in set_a.rglob('*'):
            if src.is_file():
                rel = src.relative_to(set_a)
                dest = target_a / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dest)

        for src in set_b.rglob('*'):
            if src.is_file():
                rel = src.relative_to(set_b)
                dest = target_b / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dest)

        job.set_a_label = f"{sample_name}-A"
        job.set_b_label = f"{sample_name}-B"
        await self._session.commit()
        return {"status": "ok"}

    @staticmethod
    def _sanitize_label(label: str, fallback: str) -> str:
        if not label:
            return fallback
        cleaned = re.sub(r"[^A-Za-z0-9_-]+", "-", label.strip())
        return cleaned.strip("-") or fallback

    @staticmethod
    def _display_id(job: Job) -> str:
        ts = job.created_at.strftime("%Y%m%d-%H%M")
        set_a = JobService._sanitize_label(job.set_a_label or "", "setA")
        set_b = JobService._sanitize_label(job.set_b_label or "", "setB")
        return f"{ts}-{set_a}_{set_b}"

    async def cancel_job(self, job: Job) -> JobStatusMessage:
        job.status = JobStatus.cancelled
        pages = await self._page_repo.list_for_job(job.id)
        for page in pages:
            if page.task_id:
                celery_app.control.revoke(page.task_id, terminate=False)
            if page.status in {PageStatus.pending, PageStatus.running}:
                page.status = PageStatus.failed
                page.error_message = "cancelled"
        await self._session.commit()
        return JobStatusMessage(id=str(job.id), status=job.status.value, created_at=job.created_at)

    async def get_progress(self, job: Job) -> dict:
        counts = dict(await self._page_repo.count_status_for_job(job.id))
        total = sum(counts.values())
        completed = counts.get(PageStatus.done.value, 0)
        missing = counts.get(PageStatus.missing.value, 0)
        incompatible = counts.get(PageStatus.incompatible_size.value, 0)
        failed = counts.get(PageStatus.failed.value, 0)
        running = counts.get(PageStatus.running.value, 0)
        pending = counts.get(PageStatus.pending.value, 0)
        finished = completed + missing + incompatible + failed
        percent = int((finished / total) * 100) if total else 0
        return {
            "total": total,
            "finished": finished,
            "percent": percent,
            "counts": counts,
            "completed": completed,
            "missing": missing,
            "incompatible": incompatible,
            "failed": failed,
            "running": running,
            "pending": pending,
        }

    @staticmethod
    def _pair_paths(set_a: Iterable[str], set_b: Iterable[str]) -> list[dict[str, str | bool | None]]:
        set_a_set = set(set_a)
        set_b_set = set(set_b)
        all_paths = sorted(set_a_set | set_b_set)
        pairs: list[dict[str, str | bool | None]] = []
        for rel in all_paths:
            in_a = rel in set_a_set
            in_b = rel in set_b_set
            pairs.append(
                {
                    "relative_path": rel,
                    "set_a_path": rel if in_a else None,
                    "set_b_path": rel if in_b else None,
                    "missing_in_set_a": not in_a,
                    "missing_in_set_b": not in_b,
                }
            )
        return pairs

    @staticmethod
    def _job_dir(job_id: str, set_name: str) -> Path:
        if set_name not in {"setA", "setB"}:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid set")
        return Path(settings.data_dir) / "jobs" / job_id / set_name

    async def generate_report(self, job: Job) -> bytes:
        """Generate a comprehensive PDF comparison report"""
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.units import inch
        from reportlab.pdfgen import canvas
        from PIL import Image
        
        job_dir = Path(settings.data_dir) / "jobs" / str(job.id)
        artifacts_dir = job_dir / "artifacts"
        
        # Collect all files and their diffs
        files = await self._file_repo.list_for_job(job.id)
        
        # Create temporary directory for report files
        report_dir = job_dir / "temp_report"
        report_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # Generate PDF report
            pdf_path = report_dir / "diff_report.pdf"
            c = canvas.Canvas(str(pdf_path), pagesize=letter)
            width, height = letter
            
            # Title page
            c.setFont("Helvetica-Bold", 24)
            c.drawString(1*inch, height - 1.5*inch, "PDF Diff Report")
            c.setFont("Helvetica", 12)
            c.drawString(1*inch, height - 2*inch, f"Job ID: {self._display_id(job)}")
            c.drawString(1*inch, height - 2.3*inch, f"Set A: {job.set_a_label or 'setA'}")
            c.drawString(1*inch, height - 2.6*inch, f"Set B: {job.set_b_label or 'setB'}")
            c.drawString(1*inch, height - 2.9*inch, f"Created: {job.created_at.strftime('%Y-%m-%d %H:%M:%S') if job.created_at else 'N/A'}")
            c.drawString(1*inch, height - 3.2*inch, f"Status: {job.status.value}")
            
            c.showPage()

            # Preload pages for TOC and reporting
            file_pages: list[tuple[JobFile, list]] = []
            for file_item in files:
                pages = await self._page_repo.list_for_file(str(file_item.id))
                pages = sorted(pages, key=lambda p: p.page_index)
                if pages:
                    file_pages.append((file_item, pages))

            # Table of contents (starts on first page after initial info)
            toc_entries = []
            for file_item, pages in file_pages:
                diffs_count = sum(1 for p in pages if p.diff_score and p.diff_score > 0)
                pages_with_diffs = [p for p in pages if p.diff_score and p.diff_score > 0 and p.overlay_svg_path]
                toc_entries.append({
                    "file_item": file_item,
                    "pages": pages,
                    "diffs_count": diffs_count,
                    "pages_with_diffs": pages_with_diffs,
                    "bookmark": f"file_{file_item.id}",
                    "section_pages": 1 + len(pages_with_diffs)
                })

            toc_start_y = height - 1.6*inch
            toc_bottom_y = 1*inch
            toc_line_height = 0.28 * inch
            toc_lines_per_page = max(1, int((toc_start_y - toc_bottom_y) / toc_line_height))
            toc_pages = (len(toc_entries) + toc_lines_per_page - 1) // toc_lines_per_page if toc_entries else 1

            # Compute page numbers for each entry
            current_page_number = 1 + toc_pages + 1  # title page + TOC pages + first content page
            for entry in toc_entries:
                entry["page_number"] = current_page_number
                current_page_number += entry["section_pages"]

            # Render TOC pages
            for toc_page_index in range(toc_pages):
                c.setFont("Helvetica-Bold", 18)
                c.drawString(0.75*inch, height - 1*inch, "Table of Contents")
                c.setFont("Helvetica", 11)
                y_pos = toc_start_y

                start_idx = toc_page_index * toc_lines_per_page
                end_idx = start_idx + toc_lines_per_page
                page_entries = toc_entries[start_idx:end_idx]

                for entry in page_entries:
                    file_item = entry["file_item"]
                    label = file_item.relative_path
                    page_number = entry["page_number"]
                    status = ""
                    if file_item.missing_in_set_a:
                        status = " (Missing in Set A)"
                    elif file_item.missing_in_set_b:
                        status = " (Missing in Set B)"

                    text = f"{label}{status}"
                    c.drawString(0.75*inch, y_pos, text)
                    c.drawRightString(width - 0.75*inch, y_pos, str(page_number))

                    # Link to file section
                    c.linkRect(
                        "",
                        entry["bookmark"],
                        (0.75*inch, y_pos - 2, width - 0.75*inch, y_pos + 10),
                        relative=1,
                        thickness=0
                    )

                    y_pos -= toc_line_height

                c.showPage()
            
            # Process each file
            for entry in toc_entries:
                file_item = entry["file_item"]
                pages = entry["pages"]
                
                if pages:
                    # File overview page
                    c.bookmarkPage(entry["bookmark"])
                    c.setFont("Helvetica-Bold", 16)
                    c.drawString(0.75*inch, height - 1*inch, f"File: {file_item.relative_path}")
                    c.setFont("Helvetica", 11)
                    y_pos = height - 1.5*inch
                    
                    if file_item.missing_in_set_a:
                        c.drawString(0.75*inch, y_pos, "Status: Missing in Set A")
                        y_pos -= 0.3*inch
                    elif file_item.missing_in_set_b:
                        c.drawString(0.75*inch, y_pos, "Status: Missing in Set B")
                        y_pos -= 0.3*inch
                    else:
                        c.drawString(0.75*inch, y_pos, f"Total Pages: {len(pages)}")
                        y_pos -= 0.3*inch
                        
                        diffs_count = sum(1 for p in pages if p.diff_score and p.diff_score > 0)
                        c.drawString(0.75*inch, y_pos, f"Pages with Diffs: {diffs_count}")
                        y_pos -= 0.3*inch
                    
                    c.showPage()
                    
                    # Process pages with diffs
                    for page in pages:
                        # Only show pages with diffs in PDF
                        if page.diff_score and page.diff_score > 0 and page.overlay_svg_path:
                            overlay_path = job_dir / "artifacts" / str(file_item.id) / f"page_{page.page_index}.svg"
                            
                            if overlay_path.exists():
                                c.setFont("Helvetica-Bold", 14)
                                c.drawString(0.75*inch, height - 1*inch, f"Page {page.page_index + 1} - Diff Score: {page.diff_score:.2f}")
                                
                                try:
                                    import fitz
                                    import numpy as np
                                    from PIL import ImageDraw
                                    import xml.etree.ElementTree as ET
                                    
                                    # Get PDF paths for both sets
                                    pdf_path_a = job_dir / "setA" / file_item.set_a_path if file_item.set_a_path else None
                                    pdf_path_b = job_dir / "setB" / file_item.set_b_path if file_item.set_b_path else None
                                    
                                    img_a = None
                                    img_b = None
                                    
                                    # Render Set A
                                    if pdf_path_a and pdf_path_a.exists():
                                        with fitz.open(pdf_path_a) as doc:
                                            if page.page_index < doc.page_count:
                                                pdf_page = doc.load_page(page.page_index)
                                                mat = fitz.Matrix(2.0, 2.0)
                                                pix = pdf_page.get_pixmap(matrix=mat, alpha=False)
                                                img_a = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                                    
                                    # Render Set B
                                    if pdf_path_b and pdf_path_b.exists():
                                        with fitz.open(pdf_path_b) as doc:
                                            if page.page_index < doc.page_count:
                                                pdf_page = doc.load_page(page.page_index)
                                                mat = fitz.Matrix(2.0, 2.0)
                                                pix = pdf_page.get_pixmap(matrix=mat, alpha=False)
                                                img_b = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                                    
                                    # Parse SVG to get circle positions and determine scale factor
                                    circles = []
                                    tree = ET.parse(str(overlay_path))
                                    root = tree.getroot()
                                    ns = {'svg': 'http://www.w3.org/2000/svg'}
                                    
                                    # Get SVG viewBox dimensions
                                    viewBox = root.get('viewBox', '0 0 1275 1650').split()
                                    svg_width = float(viewBox[2])
                                    svg_height = float(viewBox[3])
                                    
                                    # Calculate scale factor based on actual rendered image size
                                    if img_a:
                                        scale_x = img_a.size[0] / svg_width
                                        scale_y = img_a.size[1] / svg_height
                                    elif img_b:
                                        scale_x = img_b.size[0] / svg_width
                                        scale_y = img_b.size[1] / svg_height
                                    else:
                                        scale_x = scale_y = 1.0
                                    
                                    for circle in root.findall('.//svg:circle', ns) or root.findall('.//circle'):
                                        circles.append({
                                            'cx': float(circle.get('cx', 0)) * scale_x,
                                            'cy': float(circle.get('cy', 0)) * scale_y,
                                            'r': float(circle.get('r', 30)) * scale_x
                                        })
                                    
                                    # Draw circles on both images
                                    if img_a:
                                        draw = ImageDraw.Draw(img_a)
                                        for circ in circles:
                                            draw.ellipse(
                                                [circ['cx'] - circ['r'], circ['cy'] - circ['r'], 
                                                 circ['cx'] + circ['r'], circ['cy'] + circ['r']],
                                                outline='red', width=8
                                            )
                                    
                                    if img_b:
                                        draw = ImageDraw.Draw(img_b)
                                        for circ in circles:
                                            draw.ellipse(
                                                [circ['cx'] - circ['r'], circ['cy'] - circ['r'], 
                                                 circ['cx'] + circ['r'], circ['cy'] + circ['r']],
                                                outline='red', width=8
                                            )
                                    
                                    # Calculate bounding box around all circles with padding
                                    if circles:
                                        padding = 100  # pixels of padding around diffs
                                        min_x = min(c['cx'] - c['r'] for c in circles) - padding
                                        min_y = min(c['cy'] - c['r'] for c in circles) - padding
                                        max_x = max(c['cx'] + c['r'] for c in circles) + padding
                                        max_y = max(c['cy'] + c['r'] for c in circles) + padding
                                        
                                        # Ensure bounds are within image
                                        if img_a:
                                            min_x = max(0, min_x)
                                            min_y = max(0, min_y)
                                            max_x = min(img_a.size[0], max_x)
                                            max_y = min(img_a.size[1], max_y)
                                            
                                            # Crop to diff region
                                            img_a = img_a.crop((min_x, min_y, max_x, max_y))
                                        
                                        if img_b:
                                            img_b = img_b.crop((min_x, min_y, max_x, max_y))
                                    
                                    # Layout: Show both images side by side if both exist
                                    if img_a and img_b:
                                        # Save both images as JPEG for smaller file size
                                        img_a_file = report_dir / f"page_a_{file_item.id}_{page.page_index}.jpg"
                                        img_b_file = report_dir / f"page_b_{file_item.id}_{page.page_index}.jpg"
                                        img_a.save(img_a_file, 'JPEG', quality=85, optimize=True)
                                        img_b.save(img_b_file, 'JPEG', quality=85, optimize=True)
                                        
                                        # Calculate dimensions - each image gets half the width
                                        img_width, img_height = img_a.size
                                        max_width = 3 * inch  # Half page for each
                                        max_height = 7 * inch
                                        scale = min(max_width / img_width, max_height / img_height)
                                        
                                        final_width = img_width * scale
                                        final_height = img_height * scale
                                        
                                        y_pos = height - 1.5*inch - final_height
                                        
                                        # Draw Set A on left
                                        c.drawString(0.75*inch, height - 1.3*inch, f"Set A: {job.set_a_label or 'setA'}")
                                        c.drawImage(str(img_a_file), 0.75*inch, y_pos, width=final_width, height=final_height)
                                        
                                        # Draw Set B on right
                                        c.drawString(4.25*inch, height - 1.3*inch, f"Set B: {job.set_b_label or 'setB'}")
                                        c.drawImage(str(img_b_file), 4.25*inch, y_pos, width=final_width, height=final_height)
                                    
                                    elif img_a or img_b:
                                        # Only one version available
                                        img = img_a or img_b
                                        label = f"Set A: {job.set_a_label or 'setA'}" if img_a else f"Set B: {job.set_b_label or 'setB'}"
                                        img_file = report_dir / f"page_{file_item.id}_{page.page_index}.jpg"
                                        img.save(img_file, 'JPEG', quality=85, optimize=True)
                                        
                                        img_width, img_height = img.size
                                        max_width = 6.5 * inch
                                        max_height = 8 * inch
                                        scale = min(max_width / img_width, max_height / img_height)
                                        
                                        final_width = img_width * scale
                                        final_height = img_height * scale
                                        
                                        c.drawString(0.75*inch, height - 1.3*inch, label)
                                        c.drawImage(str(img_file), 0.75*inch, height - 1.5*inch - final_height, 
                                                  width=final_width, height=final_height)
                                    else:
                                        c.setFont("Helvetica", 10)
                                        c.drawString(0.75*inch, height - 2*inch, "No PDF files found")
                                        
                                except Exception as e:
                                    c.setFont("Helvetica", 10)
                                    c.drawString(0.75*inch, height - 2*inch, f"Error: {str(e)}")
                                
                                c.showPage()
            
            c.save()
            
            # Return PDF bytes directly
            with open(pdf_path, 'rb') as f:
                return f.read()
            
        finally:
            # Cleanup temp directory
            if report_dir.exists():
                shutil.rmtree(report_dir)
