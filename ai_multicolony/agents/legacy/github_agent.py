"""
🐙 GitHub Agent - GitHub API Integration & Repository Management
Automated Git operations, PR management, and CI/CD coordination

Made with ❤️ by Mulky Malikul Dhaher in Indonesia 🇮🇩
"""

import asyncio
import os
import json
import time
import base64
from datetime import datetime
from typing import Dict, List, Any, Optional

# Optional dependency: aiohttp for async HTTP
try:
    import aiohttp
    _AIOHTTP_AVAILABLE = True
except ImportError:
    _AIOHTTP_AVAILABLE = False


class GitHubAgent:
    """
    GitHub Integration Agent that:
    - Lists repos, branches, and commits for a configured user
    - Creates, reads, and updates files in repos via the GitHub REST API
    - Creates pull requests and issues
    - Retrieves repo status and CI information
    - Handles GitHub API rate limiting gracefully
    - Uses configurable token from GITHUB_TOKEN environment variable
    """

    API_BASE = "https://api.github.com"

    def __init__(self):
        self.agent_id = "github_agent"
        self.name = "GitHub Agent"
        self.status = "ready"
        self.capabilities = [
            "git_operations",
            "repo_management",
            "ci_cd",
            "code_sync",
            "pull_requests",
            "issue_tracking",
            "file_operations",
            "branch_management",
        ]

        # Configuration
        self.token = os.getenv("GITHUB_TOKEN", "")
        self.default_owner = os.getenv("GITHUB_DEFAULT_OWNER", "")
        self.default_repo = os.getenv("GITHUB_DEFAULT_REPO", "")

        # Rate-limit tracking
        self._rate_limit_remaining: int = 5000
        self._rate_limit_reset: Optional[float] = None

        # Performance / operational tracking
        self._stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "rate_limit_waits": 0,
            "avg_response_time": 0.0,
        }

        # Session is created lazily per event-loop to avoid cross-loop issues
        self._session: Optional[Any] = None

    # ------------------------------------------------------------------
    # Internal HTTP helpers
    # ------------------------------------------------------------------

    async def _get_session(self) -> Any:
        """Return (or create) an aiohttp ClientSession."""
        if not _AIOHTTP_AVAILABLE:
            return None
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers=self._build_headers(),
                timeout=aiohttp.ClientTimeout(total=30),
            )
        return self._session

    def _build_headers(self) -> Dict[str, str]:
        """Build common request headers."""
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    async def _request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        """
        Low-level GitHub API request with rate-limit awareness.

        Returns the parsed JSON body on success, or an error dict on failure.
        """
        if not _AIOHTTP_AVAILABLE:
            return {"success": False, "error": "aiohttp is not installed"}

        # Rate-limit gate
        if self._rate_limit_remaining <= 1 and self._rate_limit_reset:
            wait_seconds = max(0, self._rate_limit_reset - time.time()) + 1
            if wait_seconds < 300:  # only wait up to 5 min
                self._stats["rate_limit_waits"] += 1
                await asyncio.sleep(wait_seconds)
            else:
                return {
                    "success": False,
                    "error": f"GitHub API rate limit exceeded; reset in {wait_seconds:.0f}s",
                }

        url = f"{self.API_BASE}{path}"
        session = await self._get_session()
        start = time.time()

        try:
            async with session.request(method, url, **kwargs) as resp:
                elapsed = time.time() - start
                self._stats["total_requests"] += 1

                # Track rate-limit headers
                self._rate_limit_remaining = int(
                    resp.headers.get("X-RateLimit-Remaining", self._rate_limit_remaining)
                )
                reset_epoch = resp.headers.get("X-RateLimit-Reset")
                if reset_epoch:
                    self._rate_limit_reset = float(reset_epoch)

                body = await resp.text()

                if resp.status >= 400:
                    self._stats["failed_requests"] += 1
                    try:
                        err_json = json.loads(body)
                        message = err_json.get("message", body[:300])
                    except json.JSONDecodeError:
                        message = body[:300]
                    return {
                        "success": False,
                        "status": resp.status,
                        "error": message,
                    }

                self._stats["successful_requests"] += 1
                self._update_avg_response_time(elapsed)

                try:
                    data = json.loads(body)
                except json.JSONDecodeError:
                    data = body

                return {"success": True, "status": resp.status, "data": data}

        except asyncio.TimeoutError:
            self._stats["failed_requests"] += 1
            return {"success": False, "error": "Request timed out"}
        except Exception as exc:
            self._stats["failed_requests"] += 1
            return {"success": False, "error": str(exc)}

    async def _get(self, path: str, **kwargs) -> Dict[str, Any]:
        return await self._request("GET", path, **kwargs)

    async def _post(self, path: str, **kwargs) -> Dict[str, Any]:
        return await self._request("POST", path, **kwargs)

    async def _put(self, path: str, **kwargs) -> Dict[str, Any]:
        return await self._request("PUT", path, **kwargs)

    async def _patch(self, path: str, **kwargs) -> Dict[str, Any]:
        return await self._request("PATCH", path, **kwargs)

    async def _delete(self, path: str, **kwargs) -> Dict[str, Any]:
        return await self._request("DELETE", path, **kwargs)

    # ------------------------------------------------------------------
    # Public task dispatcher
    # ------------------------------------------------------------------

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Route a task dictionary to the appropriate handler."""
        try:
            action = task.get("action", "list_repos")

            handlers = {
                "list_repos": self._list_repos,
                "list_branches": self._list_branches,
                "list_commits": self._list_commits,
                "get_file": self._get_file,
                "create_file": self._create_file,
                "update_file": self._update_file,
                "delete_file": self._delete_file,
                "create_pull_request": self._create_pull_request,
                "list_pull_requests": self._list_pull_requests,
                "create_issue": self._create_issue,
                "list_issues": self._list_issues,
                "repo_status": self._repo_status,
                "ci_status": self._ci_status,
                "search_code": self._search_code,
                "get_rate_limit": self._get_rate_limit_status,
            }

            handler = handlers.get(action)
            if handler is None:
                return self._create_error_response(f"Unknown action: {action}")

            return await handler(task)

        except Exception as exc:
            return self._create_error_response(str(exc))

    # ------------------------------------------------------------------
    # Action handlers
    # ------------------------------------------------------------------

    async def _list_repos(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """List repositories for a user or organisation."""
        owner = task.get("owner", self.default_owner)
        repo_type = task.get("type", "owner")  # all, owner, member
        per_page = min(task.get("per_page", 30), 100)
        page = task.get("page", 1)

        if not owner:
            # Authenticated user's repos
            path = f"/user/repos?type={repo_type}&per_page={per_page}&page={page}"
        else:
            path = f"/users/{owner}/repos?type={repo_type}&per_page={per_page}&page={page}"

        result = await self._get(path)
        if not result.get("success"):
            return result

        repos = result["data"]
        summary = [
            {
                "name": r.get("name"),
                "full_name": r.get("full_name"),
                "private": r.get("private"),
                "description": r.get("description", ""),
                "language": r.get("language"),
                "stars": r.get("stargazers_count", 0),
                "forks": r.get("forks_count", 0),
                "default_branch": r.get("default_branch"),
                "updated_at": r.get("updated_at"),
                "url": r.get("html_url"),
            }
            for r in repos
        ]

        return {
            "success": True,
            "owner": owner,
            "total": len(summary),
            "repositories": summary,
        }

    async def _list_branches(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """List branches of a repository."""
        owner = task.get("owner", self.default_owner)
        repo = task.get("repo", self.default_repo)
        if not owner or not repo:
            return self._create_error_response("owner and repo are required")

        result = await self._get(f"/repos/{owner}/{repo}/branches")
        if not result.get("success"):
            return result

        branches = [
            {
                "name": b.get("name"),
                "protected": b.get("protected", False),
                "sha": b.get("commit", {}).get("sha"),
            }
            for b in result["data"]
        ]
        return {"success": True, "owner": owner, "repo": repo, "branches": branches}

    async def _list_commits(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """List commits on a repository branch."""
        owner = task.get("owner", self.default_owner)
        repo = task.get("repo", self.default_repo)
        if not owner or not repo:
            return self._create_error_response("owner and repo are required")

        branch = task.get("branch", "")
        per_page = min(task.get("per_page", 30), 100)

        path = f"/repos/{owner}/{repo}/commits?per_page={per_page}"
        if branch:
            path += f"&sha={branch}"

        result = await self._get(path)
        if not result.get("success"):
            return result

        commits = [
            {
                "sha": c.get("sha"),
                "message": c.get("commit", {}).get("message", "").split("\n")[0],
                "author": c.get("commit", {}).get("author", {}).get("name"),
                "date": c.get("commit", {}).get("author", {}).get("date"),
                "url": c.get("html_url"),
            }
            for c in result["data"]
        ]
        return {"success": True, "owner": owner, "repo": repo, "commits": commits}

    async def _get_file(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Read a file from a repository."""
        owner = task.get("owner", self.default_owner)
        repo = task.get("repo", self.default_repo)
        file_path = task.get("path", "")
        branch = task.get("branch", "")

        if not owner or not repo or not file_path:
            return self._create_error_response("owner, repo, and path are required")

        path = f"/repos/{owner}/{repo}/contents/{file_path}"
        if branch:
            path += f"?ref={branch}"

        result = await self._get(path)
        if not result.get("success"):
            return result

        data = result["data"]
        if isinstance(data, list):
            # Directory listing
            contents = [
                {
                    "name": item.get("name"),
                    "type": item.get("type"),
                    "path": item.get("path"),
                    "size": item.get("size"),
                }
                for item in data
            ]
            return {"success": True, "type": "directory", "contents": contents}

        # Single file
        encoding = data.get("encoding", "")
        raw_content = data.get("content", "")
        decoded = ""
        if encoding == "base64":
            try:
                decoded = base64.b64decode(raw_content).decode("utf-8", errors="replace")
            except Exception:
                decoded = raw_content

        return {
            "success": True,
            "type": "file",
            "name": data.get("name"),
            "path": data.get("path"),
            "size": data.get("size"),
            "sha": data.get("sha"),
            "content": decoded,
            "encoding": "utf-8",
        }

    async def _create_file(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new file in a repository."""
        owner = task.get("owner", self.default_owner)
        repo = task.get("repo", self.default_repo)
        file_path = task.get("path", "")
        content = task.get("content", "")
        message = task.get("message", f"Create {file_path}")
        branch = task.get("branch", "main")

        if not owner or not repo or not file_path:
            return self._create_error_response("owner, repo, and path are required")

        encoded_content = base64.b64encode(content.encode("utf-8")).decode("utf-8")
        payload = {
            "message": message,
            "content": encoded_content,
            "branch": branch,
        }

        result = await self._put(
            f"/repos/{owner}/{repo}/contents/{file_path}",
            json=payload,
        )
        if not result.get("success"):
            return result

        commit = result["data"].get("commit", {})
        return {
            "success": True,
            "path": file_path,
            "branch": branch,
            "commit_sha": commit.get("sha"),
            "commit_url": commit.get("html_url"),
        }

    async def _update_file(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing file in a repository (requires the file's current SHA)."""
        owner = task.get("owner", self.default_owner)
        repo = task.get("repo", self.default_repo)
        file_path = task.get("path", "")
        content = task.get("content", "")
        message = task.get("message", f"Update {file_path}")
        branch = task.get("branch", "main")
        sha = task.get("sha", "")

        if not owner or not repo or not file_path:
            return self._create_error_response("owner, repo, and path are required")

        # Auto-fetch SHA if not provided
        if not sha:
            file_info = await self._get_file(
                {"owner": owner, "repo": repo, "path": file_path, "branch": branch}
            )
            if not file_info.get("success"):
                return file_info
            sha = file_info.get("sha", "")
            if not sha:
                return self._create_error_response("Could not determine file SHA for update")

        encoded_content = base64.b64encode(content.encode("utf-8")).decode("utf-8")
        payload = {
            "message": message,
            "content": encoded_content,
            "sha": sha,
            "branch": branch,
        }

        result = await self._put(
            f"/repos/{owner}/{repo}/contents/{file_path}",
            json=payload,
        )
        if not result.get("success"):
            return result

        commit = result["data"].get("commit", {})
        return {
            "success": True,
            "path": file_path,
            "branch": branch,
            "commit_sha": commit.get("sha"),
            "commit_url": commit.get("html_url"),
        }

    async def _delete_file(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Delete a file from a repository."""
        owner = task.get("owner", self.default_owner)
        repo = task.get("repo", self.default_repo)
        file_path = task.get("path", "")
        message = task.get("message", f"Delete {file_path}")
        branch = task.get("branch", "main")
        sha = task.get("sha", "")

        if not owner or not repo or not file_path:
            return self._create_error_response("owner, repo, and path are required")

        if not sha:
            file_info = await self._get_file(
                {"owner": owner, "repo": repo, "path": file_path, "branch": branch}
            )
            if not file_info.get("success"):
                return file_info
            sha = file_info.get("sha", "")
            if not sha:
                return self._create_error_response("Could not determine file SHA for deletion")

        payload = {"message": message, "sha": sha, "branch": branch}

        result = await self._delete(
            f"/repos/{owner}/{repo}/contents/{file_path}", json=payload
        )
        if not result.get("success"):
            return result

        commit = result["data"].get("commit", {})
        return {
            "success": True,
            "path": file_path,
            "branch": branch,
            "commit_sha": commit.get("sha"),
        }

    async def _create_pull_request(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Create a pull request."""
        owner = task.get("owner", self.default_owner)
        repo = task.get("repo", self.default_repo)
        title = task.get("title", "")
        body = task.get("body", "")
        head = task.get("head", "")
        base = task.get("base", "main")
        draft = task.get("draft", False)

        if not owner or not repo or not title or not head:
            return self._create_error_response("owner, repo, title, and head branch are required")

        payload = {
            "title": title,
            "body": body,
            "head": head,
            "base": base,
            "draft": draft,
        }

        result = await self._post(f"/repos/{owner}/{repo}/pulls", json=payload)
        if not result.get("success"):
            return result

        pr = result["data"]
        return {
            "success": True,
            "pr_number": pr.get("number"),
            "pr_url": pr.get("html_url"),
            "state": pr.get("state"),
            "title": pr.get("title"),
            "head": pr.get("head", {}).get("ref"),
            "base": pr.get("base", {}).get("ref"),
        }

    async def _list_pull_requests(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """List pull requests for a repository."""
        owner = task.get("owner", self.default_owner)
        repo = task.get("repo", self.default_repo)
        state = task.get("state", "open")  # open, closed, all
        per_page = min(task.get("per_page", 30), 100)

        if not owner or not repo:
            return self._create_error_response("owner and repo are required")

        result = await self._get(
            f"/repos/{owner}/{repo}/pulls?state={state}&per_page={per_page}"
        )
        if not result.get("success"):
            return result

        prs = [
            {
                "number": pr.get("number"),
                "title": pr.get("title"),
                "state": pr.get("state"),
                "user": pr.get("user", {}).get("login"),
                "head": pr.get("head", {}).get("ref"),
                "base": pr.get("base", {}).get("ref"),
                "created_at": pr.get("created_at"),
                "url": pr.get("html_url"),
            }
            for pr in result["data"]
        ]
        return {"success": True, "owner": owner, "repo": repo, "pull_requests": prs}

    async def _create_issue(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Create an issue in a repository."""
        owner = task.get("owner", self.default_owner)
        repo = task.get("repo", self.default_repo)
        title = task.get("title", "")
        body = task.get("body", "")
        labels = task.get("labels", [])
        assignees = task.get("assignees", [])

        if not owner or not repo or not title:
            return self._create_error_response("owner, repo, and title are required")

        payload: Dict[str, Any] = {"title": title, "body": body}
        if labels:
            payload["labels"] = labels
        if assignees:
            payload["assignees"] = assignees

        result = await self._post(f"/repos/{owner}/{repo}/issues", json=payload)
        if not result.get("success"):
            return result

        issue = result["data"]
        return {
            "success": True,
            "issue_number": issue.get("number"),
            "issue_url": issue.get("html_url"),
            "state": issue.get("state"),
            "title": issue.get("title"),
        }

    async def _list_issues(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """List issues for a repository."""
        owner = task.get("owner", self.default_owner)
        repo = task.get("repo", self.default_repo)
        state = task.get("state", "open")
        per_page = min(task.get("per_page", 30), 100)

        if not owner or not repo:
            return self._create_error_response("owner and repo are required")

        result = await self._get(
            f"/repos/{owner}/{repo}/issues?state={state}&per_page={per_page}"
        )
        if not result.get("success"):
            return result

        issues = [
            {
                "number": i.get("number"),
                "title": i.get("title"),
                "state": i.get("state"),
                "user": i.get("user", {}).get("login"),
                "labels": [l.get("name") for l in i.get("labels", [])],
                "created_at": i.get("created_at"),
                "url": i.get("html_url"),
            }
            for i in result["data"]
            if "pull_request" not in i  # exclude PRs from issue list
        ]
        return {"success": True, "owner": owner, "repo": repo, "issues": issues}

    async def _repo_status(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Get high-level repository status including recent activity."""
        owner = task.get("owner", self.default_owner)
        repo = task.get("repo", self.default_repo)
        if not owner or not repo:
            return self._create_error_response("owner and repo are required")

        repo_result = await self._get(f"/repos/{owner}/{repo}")
        if not repo_result.get("success"):
            return repo_result

        r = repo_result["data"]
        return {
            "success": True,
            "full_name": r.get("full_name"),
            "description": r.get("description"),
            "private": r.get("private"),
            "default_branch": r.get("default_branch"),
            "language": r.get("language"),
            "stars": r.get("stargazers_count"),
            "forks": r.get("forks_count"),
            "open_issues_count": r.get("open_issues_count"),
            "watchers": r.get("watchers_count"),
            "created_at": r.get("created_at"),
            "updated_at": r.get("updated_at"),
            "pushed_at": r.get("pushed_at"),
            "url": r.get("html_url"),
        }

    async def _ci_status(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Get the combined CI status for a repository / ref."""
        owner = task.get("owner", self.default_owner)
        repo = task.get("repo", self.default_repo)
        ref = task.get("ref", "")

        if not owner or not repo:
            return self._create_error_response("owner and repo are required")

        if not ref:
            # Default to default branch
            repo_info = await self._repo_status(task)
            ref = repo_info.get("default_branch", "main") if repo_info.get("success") else "main"

        # Combined status
        combined = await self._get(f"/repos/{owner}/{repo}/commits/{ref}/status")

        # Check runs (GitHub Actions)
        check_runs = await self._get(
            f"/repos/{owner}/{repo}/commits/{ref}/check-runs?per_page=20"
        )

        statuses = []
        if combined.get("success"):
            for s in combined["data"].get("statuses", []):
                statuses.append(
                    {
                        "context": s.get("context"),
                        "state": s.get("state"),
                        "description": s.get("description"),
                        "target_url": s.get("target_url"),
                    }
                )

        checks = []
        if check_runs.get("success"):
            for cr in check_runs["data"].get("check_runs", []):
                checks.append(
                    {
                        "name": cr.get("name"),
                        "status": cr.get("status"),
                        "conclusion": cr.get("conclusion"),
                        "url": cr.get("html_url"),
                    }
                )

        overall_state = combined["data"].get("state", "unknown") if combined.get("success") else "unknown"

        return {
            "success": True,
            "ref": ref,
            "overall_state": overall_state,
            "statuses": statuses,
            "check_runs": checks,
        }

    async def _search_code(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Search code across GitHub."""
        query = task.get("query", "")
        if not query:
            return self._create_error_response("query is required")

        per_page = min(task.get("per_page", 30), 100)
        result = await self._get(f"/search/code?q={query}&per_page={per_page}")
        if not result.get("success"):
            return result

        items = [
            {
                "name": i.get("name"),
                "path": i.get("path"),
                "repository": i.get("repository", {}).get("full_name"),
                "url": i.get("html_url"),
            }
            for i in result["data"].get("items", [])
        ]
        return {
            "success": True,
            "total_count": result["data"].get("total_count", 0),
            "results": items,
        }

    async def _get_rate_limit_status(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Return the current GitHub API rate-limit status."""
        result = await self._get("/rate_limit")
        if not result.get("success"):
            return result

        core = result["data"].get("resources", {}).get("core", {})
        return {
            "success": True,
            "limit": core.get("limit"),
            "remaining": core.get("remaining"),
            "reset": core.get("reset"),
            "used": core.get("used"),
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _update_avg_response_time(self, elapsed: float):
        """Keep a running average of API response times."""
        total = self._stats["total_requests"]
        current_avg = self._stats["avg_response_time"]
        self._stats["avg_response_time"] = (current_avg * (total - 1) + elapsed) / total

    def _create_error_response(self, error_message: str) -> Dict[str, Any]:
        """Create a standardized error response."""
        self._stats["failed_requests"] += 1
        return {
            "success": False,
            "error": error_message,
            "timestamp": datetime.now().isoformat(),
            "agent": self.agent_id,
        }

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Return agent performance metrics."""
        return {
            "agent_id": self.agent_id,
            "status": self.status,
            "capabilities": self.capabilities,
            "api_stats": self._stats,
            "rate_limit_remaining": self._rate_limit_remaining,
            "token_configured": bool(self.token),
            "default_owner": self.default_owner,
        }

    async def close(self):
        """Clean up the aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()


# Global instance
github_agent = GitHubAgent()
