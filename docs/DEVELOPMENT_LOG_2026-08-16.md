# FixCare Development Log — 2026-08-16

## Purpose

This document records the major debugging work completed during the FixCare Flutter ↔ FastAPI integration session on 16 August 2026. It is intended to make the current checkpoint reproducible and prevent previously solved problems from being reintroduced.

---

## 1. Starting point

The project is a Flutter frontend backed by FastAPI, PostgreSQL, SQLAlchemy/Alembic, and an AI-provider abstraction.

The work for this session focused primarily on the diagnosis flow and the contract between Flutter and FastAPI.

The repository checkpoint was committed as:

```text
963f7923720d8fb0eb72e6ff325d37190ccd9e71
checkpoint: stable frontend and backend state
```

Branch:

```text
main
```

---

## 2. Diagnosis API model mismatch

### Symptom

Flutter successfully sent a request to the backend and the backend returned HTTP `201 Created`, but Flutter failed while deserializing the response with:

```text
type 'Null' is not a subtype of type 'String' in type cast
```

Earlier, the generated `json_serializable` code expected camelCase response keys such as:

```text
deviceCategory
problemSummary
technicianRequired
createdAt
updatedAt
```

while the FastAPI/Pydantic schema uses snake_case field names:

```text
device_category
problem_summary
technician_required
created_at
updated_at
```

### Root cause

The frontend JSON contract did not consistently match the backend Pydantic contract.

### Fix

The Flutter diagnosis models were aligned with the FastAPI wire format using explicit `JsonKey` mappings for response models. The diagnosis request was also given an explicit `toJson()` implementation producing snake_case keys.

Important request keys are now:

```text
device_category
problem_description
device_id
brand
model
follow_up_answers
```

The response models explicitly map fields such as:

```text
device_category -> deviceCategory
problem_summary -> problemSummary
technician_required -> technicianRequired
technician_reason -> technicianReason
created_at -> createdAt
updated_at -> updatedAt
completed_at -> completedAt
```

### Result

The request/response contract is now explicitly controlled rather than relying on the default camelCase generated JSON names.

---

## 3. Freezed / json_serializable generation problem

### Symptom

Running code generation produced:

```text
Cannot populate the required constructor argument: deviceCategory.
```

The generator was unable to populate the required constructor argument for `DiagnosisRequest`.

Generated files were also removed during cleanup, and subsequent generation continued to fail.

### Investigation

The dependency versions were inspected. The project currently uses:

```text
build_runner 2.15.1
freezed 3.2.5
freezed_annotation 3.1.0
json_serializable 6.14.1
analyzer 10.2.0
```

The project SDK constraint is:

```text
Dart >=3.8.0 <4.0.0
Flutter >=3.24.0
```

`flutter pub upgrade` was executed and the dependency lockfile was updated.

### Important lesson

Do not repeatedly regenerate or rewrite generated files while the source model definition itself is inconsistent with the generator's expectations. Fix the source model and serialization contract first.

The diagnosis request eventually moved to an explicit manual `toJson()` implementation because the request wire format is deliberately snake_case.

---

## 4. Incorrect request payload transformation

### Symptom

FastAPI returned HTTP `422 Unprocessable Entity` with:

```text
Input should be 'mobile', 'laptop' or 'tv'
Input should be a valid string
```

The backend showed:

```text
body.device_category = None
body.problem_description = None
```

### Root cause

The Flutter remote datasource was attempting to transform a request that already needed snake_case into snake_case again using camelCase lookup keys.

The problematic pattern was effectively:

```dart
originalData['deviceCategory']
originalData['problemDescription']
```

when the request's `toJson()` was already producing:

```text
device_category
problem_description
```

That resulted in null values being sent to FastAPI.

### Fix

`DiagnosisRemoteDataSource.createDiagnosis()` was simplified to use the request's canonical serialization directly:

```dart
final data = request.toJson();

final response = await _apiClient.post<Map<String, dynamic>>(
  '/diagnosis',
  data: data,
  parser: (data) => data,
);
```

This removes a redundant transformation layer and makes the request contract single-source-of-truth.

### Result

The backend subsequently accepted the diagnosis request and returned:

```text
POST /api/v1/diagnosis HTTP/1.1 201 Created
```

---

## 5. Backend diagnosis persistence verified

The backend logs showed the diagnosis record and associated result being queried successfully.

Observed database operations included:

```text
SELECT diagnoses.id
FROM diagnoses
WHERE diagnoses.id = $1::UUID
```

and:

```text
SELECT diagnosis_results.id,
       diagnosis_results.diagnosis_id,
       diagnosis_results.possible_causes,
       diagnosis_results.safe_steps,
       diagnosis_results.risks,
       diagnosis_results.follow_up_questions,
       diagnosis_results.disclaimer,
       diagnosis_results.raw_ai_response,
       diagnosis_results.created_at
FROM diagnosis_results
WHERE $1::UUID = diagnosis_results.diagnosis_id
```

The API returned:

```text
201 Created
```

This confirms that the diagnosis request reached the backend and database persistence/querying was functioning during the checkpoint.

---

## 6. API connectivity / emulator networking investigation

### Symptom

Flutter initially displayed a generic `No Internet` error even though the FastAPI backend was running.

The Android emulator uses:

```text
10.0.2.2
```

to reach the host machine's localhost services.

The Flutter logs showed requests such as:

```text
POST http://10.0.2.2:8000/api/v1/diagnosis
```

This is the correct host-side address pattern for the Android emulator when FastAPI is listening on the host.

### Verification

FastAPI was confirmed healthy through:

```text
GET /docs  -> 200 OK
GET /openapi.json -> 200 OK
```

The backend also reported:

```text
Application startup complete.
```

The diagnosis endpoint later returned HTTP `201`, proving that the emulator-to-backend path was working during the stable checkpoint.

### Lesson

Do not treat a generic Flutter `No Internet` message as proof that the machine has no internet connection. It may represent a network/API exception produced by the client layer. Always inspect the actual HTTP request, status code, and backend logs.

---

## 7. Flutter debug launch issue

A later Flutter launch attempt produced:

```text
Error waiting for a debug connection: The log reader stopped unexpectedly
Error launching application on sdk gphone64 x86 64.
```

This was a Flutter/Android debug connection problem rather than a demonstrated Dart compilation or FastAPI backend failure.

No broad source-code rewrite was made in response. The correct decision at the checkpoint was to stop changing code and preserve the working state.

---

## 8. Previously solved backend problems

The backend checkpoint also contains these earlier fixes:

1. **API circular import** — removed the unnecessary router import from the health module.
2. **SQLAlchemy typo** — corrected `mapped.column(...)` to `mapped_column(...)`.
3. **Missing `RiskLevel` import** — added the required enum import to the diagnosis service.
4. **structlog configuration** — corrected use of the logging configuration instead of `structlog.INFO`.
5. **Alembic configuration** — added the missing `script_location` configuration.
6. **Safety severity ordering** — replaced direct string comparison with an explicit ranking:
   `SAFE < LOW < MODERATE < HIGH < CRITICAL`.
7. **Swollen-battery escalation reason** — preserved the hazard context instead of returning only a generic escalation message.
8. **PostgreSQL/Docker setup** — PostgreSQL 16 was running successfully in Docker and the initial Alembic migration was applied.
9. **Backend regression suite** — the documented backend baseline reached `37 passed, 0 failed`.
10. **JWT authentication centralization** — authentication logic was centralized in an earlier checkpoint.
11. **Diagnosis follow-up backend flow** — the follow-up flow was completed in an earlier commit.

---

## 9. Current architecture contract

The diagnosis path should remain conceptually:

```text
Flutter UI
   ↓
DiagnosisViewModel
   ↓
DiagnosisRepository
   ↓
DiagnosisRemoteDataSource
   ↓
ApiClient / Dio
   ↓
FastAPI /api/v1/diagnosis
   ↓
Diagnosis service
   ↓
Safety screening / validation
   ↓
AI provider abstraction
   ↓
PostgreSQL
   ↓
DiagnosisResponse
   ↓
Flutter models
   ↓
Diagnosis result UI
```

The important serialization rule is:

```text
Flutter internal names: camelCase
             ↓
JSON wire format: snake_case
             ↓
FastAPI/Pydantic: snake_case
```

Do not add a second conversion layer unless the contract actually changes.

---

## 10. Stable checkpoint

Repository checkpoint:

```text
963f7923720d8fb0eb72e6ff325d37190ccd9e71
```

Commit message:

```text
checkpoint: stable frontend and backend state
```

The repository was successfully pushed to GitHub at this checkpoint.

Repository:

```text
iamRealXD/FixCare
```

---

## 11. What NOT to do when resuming

Do not immediately:

```text
flutter clean
flutter pub upgrade
build_runner clean
build_runner build
rewrite diagnosis models
rewrite ApiClient
rewrite backend schemas
```

unless a specific reproducible failure requires it.

In particular, do not modify the JSON contract casually. The frontend request and backend Pydantic schema now have a known working relationship.

---

## 12. Safe resume procedure

When continuing development:

### Step 1 — Verify repository state

```powershell
git status
git log -5 --oneline
```

The stable checkpoint should be visible in history.

### Step 2 — Start backend infrastructure

```powershell
docker compose up -d postgres
```

Then:

```powershell
docker compose ps
```

### Step 3 — Start FastAPI

From `backend`:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Step 4 — Verify API

Open:

```text
http://localhost:8000/docs
```

Also verify:

```text
http://localhost:8000/openapi.json
```

### Step 5 — Start Flutter

From `frontend`:

```powershell
flutter pub get
flutter run
```

Do not regenerate code unless the source models were intentionally changed.

### Step 6 — Test diagnosis

Confirm the request log contains non-null values for:

```text
device_category
problem_description
```

Then confirm the backend returns:

```text
201 Created
```

### Step 7 — Only then continue UI work

If the API contract is healthy, continue with the diagnosis result/follow-up UI rather than changing the networking or serialization layers.

---

## 13. Git checkpoint procedure

After a verified change:

```powershell
git status
```

Review:

```powershell
git diff --stat
git diff
```

Then stage:

```powershell
git add .
```

Commit with a focused message:

```powershell
git commit -m "feat: ..."
```

Push:

```powershell
git push origin main
```

Finally verify:

```powershell
git status
```

The desired result is:

```text
nothing to commit, working tree clean
```

---

## 14. Documentation rule going forward

Every meaningful bug should be recorded with four items:

```text
Symptom
Root cause
Fix
Verification
```

Example:

```text
Symptom: FastAPI returned 422.
Root cause: Flutter datasource looked up camelCase keys after request.toJson() already produced snake_case.
Fix: Use request.toJson() directly.
Verification: POST /api/v1/diagnosis returned 201 Created.
```

This prevents repeated debugging of the same problem and makes future sessions much faster.

---

## 15. Next development target

The next session should begin from the stable checkpoint and focus on runtime verification of the complete diagnosis UX:

```text
Device selection
→ Problem input
→ Diagnosis request
→ Loading state
→ Follow-up questions when required
→ Diagnosis result
→ Safety warnings
→ History persistence
→ Feedback
```

The backend/networking/serialization layers should be considered **checkpointed**. Change them only when a new reproducible failure demonstrates that a change is necessary.
