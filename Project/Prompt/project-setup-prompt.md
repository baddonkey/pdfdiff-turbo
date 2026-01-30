# GPT-5.2-Codex Final Build Prompt

## PDF Comparison Platform (Full Stack)

You are GPT-5.2-Codex. Build a complete production-grade system as
specified below. Follow all phases sequentially. Do not skip phases.
Output full code for each file.

------------------------------------------------------------------------

## GLOBAL CONSTRAINTS (LOCKED)

-   Shared Docker volume at /data for all artifacts
-   PDF rendering via PyMuPDF (RGB, DPI scaling)
-   No scaling, padding, or cropping on size mismatch
-   Diff metric is percentage of changed pixels
-   One Celery task per page
-   Incompatible size =\> status=incompatible_size, diff_score=null
-   Missing pages explicitly tracked
-   Per-user jobs with JWT auth
-   Admin role can manage all users and jobs

------------------------------------------------------------------------

## PHASE 1 --- Infrastructure & Core

Implement: - docker-compose.yml (postgres, rabbitmq, api, worker,
flower, viewer, admin) - FastAPI base app - SQLAlchemy async models -
Alembic migrations - Celery + RabbitMQ wiring - Shared volume mounting -
Health endpoints

------------------------------------------------------------------------

## PHASE 2 --- Authentication & RBAC

Implement: - User and RefreshToken tables - JWT auth (access +
refresh) - /auth/register, /auth/login, /auth/refresh, /auth/logout,
/me - Role-based guards (user vs admin)

------------------------------------------------------------------------

## PHASE 3 --- Upload & Job Manifest

Implement: - POST /jobs - POST /jobs/{job_id}/upload?set=A\|B (ZIP +
multipart) - POST /jobs/{job_id}/start - File pairing by relative_path -
Store files under /data/jobs/{job_id}/setA\|setB

------------------------------------------------------------------------

## PHASE 4 --- Worker Pipeline

Implement Celery tasks: - run_job(job_id) - compare_page(page_result_id)
Rendering: - PyMuPDF RGB DPI scaling Diff: - abs diff per channel -
threshold mask - OpenCV morphology - bounding boxes Output: -
overlay.svg per page

------------------------------------------------------------------------

## PHASE 5 --- Cancellation & Status

Implement: - POST /jobs/{job_id}/cancel - revoke Celery tasks -
cooperative cancellation - status endpoints: - GET /jobs/{job_id} - GET
/jobs/{job_id}/files - GET /jobs/{job_id}/files/{file_id}/pages -
artifact streaming endpoints

------------------------------------------------------------------------

## PHASE 6 --- Viewer UI (Angular)

Implement: - Login/Register - Job list (per user) - File viewer: -
side-by-side PDF.js render - overlay SVG - page nav - next/prev diff -
deep links: /jobs/:jobId/files/:fileId?page=&diff=

------------------------------------------------------------------------

## PHASE 7 --- Admin UI (Angular)

Implement: - Admin login - List all jobs - Cancel any job - Manage users
(role, active)

------------------------------------------------------------------------

## PHASE 8 --- Finalization

-   Seed users
-   README with exact run steps
-   Scaling instructions
-   No TODOs

------------------------------------------------------------------------

### OUTPUT RULES

-   List every file
-   Full contents only
-   No placeholders
-   Ensure Docker works

BEGIN WITH PHASE 1.
