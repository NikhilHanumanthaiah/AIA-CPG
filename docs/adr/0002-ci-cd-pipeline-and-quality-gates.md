# ADR 0002: CI/CD Pipeline and Code Quality Gate Architecture

## Status
Accepted

## Context
As the project transitioned from initial development to hands-off maintenance, we needed to establish a robust code verification and regression prevention mechanism. The system must verify that:
1. All changes maintain consistent syntax formatting and PEP 8 import styling.
2. The entire unit and integration test suite (23 tests) passes successfully before code is merged.
3. The configuration runs efficiently in both cloud environments (GitHub Actions) and local developer terminals.

## Decisions

### 1. CI Orchestrator: GitHub Actions
* **Decision:** Implement a GitHub Actions workflow defined in `.github/workflows/ci.yml`.
* **Rationale:** Since the code is hosted on GitHub, native Actions require zero external account configurations, are highly configurable, and fall completely within the free tier (unlimited for public repositories, 2,000 minutes/month for private repositories).

### 2. Testing Isolation: In-Memory SQLite Database
* **Decision:** Configure tests to use an in-memory SQLite configuration instead of spinning up PostgreSQL docker containers during CI runs.
* **Rationale:** Spinning up PostgreSQL in CI requires container orchestration steps, credentials management, and connection waiting, which slows down the build pipeline. Using SQLite isolates testing to application memory, executing all 23 tests in under 30 seconds with zero external database dependencies.

### 3. Styling & Code Consistency Gates: Black and Isort
* **Decision:** Enforce formatting checking in the CI pipeline using `black --check .` and `isort --check-only .`.
* **Rationale:** Rather than debating code style during handoff or reviews, formatting rules are formalized in `pyproject.toml` and verified programmatically. Commits that deviate from these standards fail the pipeline and are blocked from merge.

### 4. Local Validation Helper: run_ci_locally.sh
* **Decision:** Provide an executable shell script `run_ci_locally.sh` in the repository root.
* **Rationale:** To save cloud runner minutes and accelerate developer feedback loops, developers can execute this script locally to run identical black, isort, and pytest checks in one command before committing code.

### 5. Dependency Management: Pinning `httpx2`
* **Decision:** Explicitly add `httpx2` to `requirements.txt`.
* **Rationale:** Recent Starlette versions require `httpx2` for the `TestClient` class to execute ASGI server simulations. Pinning this dependency ensures that tests run successfully on both clean virtual environments and CI runners without generating module import errors.

## Consequences
* **Automated Quality Gates:** Code cannot be merged into the `main` branch with broken formatting or failing tests.
* **Rapid CI Feedback Loop:** By separating database setups and utilizing SQLite, the entire CI pipeline completes in under 2 minutes.
* **Maintainability for Inheriting Teams:** Future engineers can clone the repository, run `./run_ci_locally.sh`, and immediately verify that their local workspace is configured correctly.
