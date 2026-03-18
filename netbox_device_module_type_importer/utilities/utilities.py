import asyncio
import aiohttp
import time
import requests
from jinja2 import Template


class GQLError(Exception):
    default_message = None

    def __init__(self, message=None):
        if message is None:
            self.message = self.default_message
        else:
            self.message = message
        super().__init__(message)


class GitHubGQLAPIAsync:
    """
    Async version of GitHubGQLAPI for parallel processing.
    Can be 3-5× faster than the synchronous version by processing multiple vendors in parallel.
    """

    tree_query = """
{
  repository(owner: "{{ owner }}", name: "{{ repo }}") {
    object(expression: "master:{{ path }}") {
      ... on Tree {
        entries {
          name
          type
        }
      }
    }
  }
}
"""
    sub_tree_query = """
{
  repository(owner: "{{ owner }}", name: "{{ repo }}") {
    object(expression: "master:{{ path }}/{{ vendor }}") {
      ... on Tree {
        entries {
          name
          type
        }
      }
    }
  }
}
"""
    file_oids_query = """
{
  repository(owner: "{{ owner }}", name: "{{ repo }}") {
    {% for file_name in file_names %}
    file_{{ loop.index0 }}: object(expression: "master:{{ path }}/{{ vendor }}/{{ file_name }}") {
      ... on Blob {
        oid
      }
    }
    {% endfor %}
  }
}
"""
    files_query = """
{
    repository(owner: "{{ owner }}", name: "{{ repo }}") {
        {% for sha, path in data.items() %}
        sha_{{ sha }}: object(expression: "master:{{ root_path }}/{{ path }}") {
            ... on Blob {
                text
            }
        }
        {% endfor %}
    }
}
"""

    def __init__(
        self,
        url="https://api.github.com/graphql",
        token=None,
        owner=None,
        repo=None,
        path="device-types",
    ):
        self.path = path
        self.url = url
        self.token = token
        self.owner = owner
        self.repo = repo
        self.headers = {"Authorization": f"token {token}"}

    async def get_query_async(self, session, query, max_retries=3, retry_delay=2):
        """Async version of get_query with retry logic."""
        result = {}
        last_error = None

        for attempt in range(max_retries):
            try:
                async with session.post(
                    self.url, json={"query": query}, headers=self.headers
                ) as response:
                    # Check for HTTP errors
                    if not response.ok:
                        if response.status == 502:
                            if attempt < max_retries - 1:
                                await asyncio.sleep(retry_delay)
                                continue
                        try:
                            error_data = await response.json()
                            raise GQLError(
                                error_data.get("message", f"HTTP {response.status}")
                            )
                        except Exception:
                            text = await response.text()
                            raise GQLError(f"HTTP {response.status}: {text[:200]}")

                    # Try to parse JSON response
                    try:
                        result = await response.json()
                    except aiohttp.ContentTypeError:
                        text = await response.text()
                        if (
                            "502 Bad Gateway" in text
                            or "503 Service Unavailable" in text
                        ):
                            if attempt < max_retries - 1:
                                await asyncio.sleep(retry_delay)
                                continue
                        raise GQLError(f"Can't parse message from GitHub. {text[:500]}")

                    # Check for GraphQL errors
                    err = result.get("errors")
                    if err:
                        error_msg = err[0].get("message")
                        if (
                            "timeout" in error_msg.lower()
                            or "temporarily unavailable" in error_msg.lower()
                        ):
                            if attempt < max_retries - 1:
                                await asyncio.sleep(retry_delay)
                                continue
                        raise GQLError(message=error_msg)

                    # Success!
                    return result

            except GQLError:
                raise
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    continue
                else:
                    raise GQLError(f"Failed after {max_retries} attempts: {e}")

        if last_error:
            raise GQLError(f"Failed after {max_retries} attempts: {last_error}")
        return result

    async def process_vendor_batches(
        self,
        session,
        vendor_name,
        file_names,
        batch_size,
        oid_template,
        verbose,
        semaphore,
    ):
        """Process all batches for a vendor in parallel."""
        result = {}
        total_batches = (len(file_names) + batch_size - 1) // batch_size

        async def fetch_batch(batch_idx, batch_files):
            """Fetch a single batch of files."""
            async with semaphore:  # Limit concurrent requests
                batch_num = batch_idx + 1
                if verbose:
                    print(
                        f"    Batch {batch_num}/{total_batches}: {len(batch_files)} files"
                    )

                try:
                    oid_query = oid_template.render(
                        owner=self.owner,
                        repo=self.repo,
                        path=self.path,
                        vendor=vendor_name,
                        file_names=batch_files,
                    )
                    oid_data = await self.get_query_async(session, oid_query)

                    if not oid_data:
                        if verbose:
                            print(
                                f"      Warning: No data returned for batch {batch_num}"
                            )
                        return None

                    # Extract OIDs
                    batch_result = {}
                    repo_data = oid_data["data"]["repository"]
                    for idx, file_name in enumerate(batch_files):
                        file_key = f"file_{idx}"
                        if file_key in repo_data and repo_data[file_key]:
                            batch_result[file_name] = {
                                "sha": repo_data[file_key]["oid"]
                            }
                    return batch_result

                except GQLError as e:
                    if verbose:
                        print(f"      Error fetching batch {batch_num}: {e}")
                    return None

        # Create tasks for all batches
        tasks = []
        for i in range(0, len(file_names), batch_size):
            batch = file_names[i : i + batch_size]
            batch_idx = i // batch_size
            tasks.append(fetch_batch(batch_idx, batch))

        # Execute all batches in parallel (with semaphore limiting concurrency)
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Combine results
        failed_batches = []
        for idx, batch_result in enumerate(batch_results):
            if isinstance(batch_result, Exception):
                if verbose:
                    print(f"      Exception in batch {idx + 1}: {batch_result}")
                failed_batches.append(idx + 1)
            elif batch_result:
                result.update(batch_result)
            else:
                failed_batches.append(idx + 1)

        if failed_batches and verbose:
            print(
                f"  Warning: Failed to fetch batches {failed_batches} for {vendor_name}"
            )

        return result

    async def process_vendor(
        self,
        session,
        vendor_name,
        sub_template,
        oid_template,
        batch_size,
        verbose,
        semaphore,
    ):
        """Process a single vendor (get file names, then fetch OIDs in parallel batches)."""
        try:
            # Get file names for this vendor
            sub_query = sub_template.render(
                owner=self.owner, repo=self.repo, path=self.path, vendor=vendor_name
            )
            vendor_data = await self.get_query_async(session, sub_query)

            if not vendor_data:
                if verbose:
                    print(f"  Warning: No data returned for {vendor_name}")
                return vendor_name, {}

            # Extract file names
            vendor_entries = vendor_data["data"]["repository"]["object"]["entries"]
            file_names = [
                entry["name"] for entry in vendor_entries if entry["type"] == "blob"
            ]

            if not file_names:
                if verbose:
                    print(f"  No files found in {vendor_name}")
                return vendor_name, {}

            if verbose:
                print(
                    f"  Found {len(file_names)} files, fetching OIDs in parallel batches of {batch_size}..."
                )

            # Fetch all batches in parallel
            result = await self.process_vendor_batches(
                session,
                vendor_name,
                file_names,
                batch_size,
                oid_template,
                verbose,
                semaphore,
            )

            return vendor_name, result

        except GQLError as e:
            if verbose:
                print(f"  Error processing vendor {vendor_name}: {e}")
            return vendor_name, {}
        except Exception as e:
            if verbose:
                print(f"  Unexpected error processing vendor {vendor_name}: {e}")
            return vendor_name, {}

    async def get_tree_async(
        self,
        batch_size=50,
        max_concurrent_requests=10,
        max_concurrent_vendors=5,
        verbose=True,
    ):
        """
        Async version of get_tree with parallel processing.

        Args:
            batch_size: Number of files to fetch per batch (default: 50)
            max_concurrent_requests: Max concurrent batch requests (default: 10)
            max_concurrent_vendors: Max vendors to process in parallel (default: 5)
            verbose: Print progress messages (default: True)

        Returns:
            Dictionary mapping vendor names to file dictionaries
        """
        result = {}

        # Create the semaphore to limit concurrent requests (avoid overwhelming API)
        semaphore = asyncio.Semaphore(max_concurrent_requests)

        async with aiohttp.ClientSession() as session:
            # Get vendor list
            template = Template(self.tree_query)
            query = template.render(owner=self.owner, repo=self.repo, path=self.path)
            data = await self.get_query_async(session, query)

            if not data:
                return result

            vendors = data["data"]["repository"]["object"]["entries"]
            vendor_list = [v for v in vendors if v["type"] == "tree"]
            total_vendors = len(vendor_list)

            if verbose:
                print(
                    f"Processing {total_vendors} vendors in parallel (max {max_concurrent_vendors} at a time)..."
                )

            # Pre-compile templates
            sub_template = Template(self.sub_tree_query)
            oid_template = Template(self.file_oids_query)

            # Process vendors in parallel (with limit)
            vendor_count = 0
            for i in range(0, len(vendor_list), max_concurrent_vendors):
                vendor_batch = vendor_list[i : i + max_concurrent_vendors]

                tasks = []
                for vendor in vendor_batch:
                    vendor_name = vendor["name"]
                    vendor_count += 1
                    if verbose:
                        print(
                            f"Processing vendor: {vendor_name} ({vendor_count}/{total_vendors})"
                        )

                    task = self.process_vendor(
                        session,
                        vendor_name,
                        sub_template,
                        oid_template,
                        batch_size,
                        verbose,
                        semaphore,
                    )
                    tasks.append(task)

                # Wait for this batch of vendors to complete
                vendor_results = await asyncio.gather(*tasks, return_exceptions=True)

                # Combine results
                for vendor_result in vendor_results:
                    if isinstance(vendor_result, Exception):
                        if verbose:
                            print(f"  Exception processing vendor: {vendor_result}")
                        continue
                    vendor_name, vendor_data = vendor_result
                    result[vendor_name] = vendor_data

        return result

    def get_tree(
        self,
        batch_size=50,
        max_concurrent_requests=10,
        max_concurrent_vendors=5,
        verbose=True,
    ):
        """
        Synchronous wrapper for async get_tree.

        Args:
            batch_size: Number of files to fetch per batch (default: 50)
            max_concurrent_requests: Max concurrent batch requests (default: 10)
            max_concurrent_vendors: Max vendors to process in parallel (default: 5)
            verbose: Print progress messages (default: True)

        Returns:
            Dictionary mapping vendor names to file dictionaries
        """
        return asyncio.run(
            self.get_tree_async(
                batch_size=batch_size,
                max_concurrent_requests=max_concurrent_requests,
                max_concurrent_vendors=max_concurrent_vendors,
                verbose=verbose,
            )
        )

    async def get_files_async(self, query_data):
        """Async version of get_files."""
        result = {}
        if not query_data:
            return result

        async with aiohttp.ClientSession() as session:
            template = Template(self.files_query)
            query = template.render(
                owner=self.owner, repo=self.repo, data=query_data, root_path=self.path
            )
            data = await self.get_query_async(session, query)
            for k, v in data["data"]["repository"].items():
                result[k.replace("sha_", "")] = v["text"]
        return result

    def get_files(self, query_data):
        """Synchronous wrapper for async get_files."""
        return asyncio.run(self.get_files_async(query_data))


class GitHubAPI:
    def __init__(self, url=None, token=None, owner=None, repo=None):
        self.session = requests.session()
        self.session.headers.update({"Accept": "application/vnd.github.v3+json"})
        if token:
            self.session.headers.update({"Authorization": f"token {token}"})
        self.dt_dir = "device-types"
        self.url = f"https://api.github.com/repos/{owner}/{repo}/contents/"

    def get_vendors(self):
        result = {}
        url = f"{self.url}{self.dt_dir}"
        response = self.session.get(url)
        if response.ok:
            for vendor in response.json():
                result[vendor["name"]] = vendor["path"]
        return result

    def get_models(self, vendor):
        result = {}
        url = f"{self.url}{self.dt_dir}/{vendor}"
        response = self.session.get(url)
        if response.ok:
            for model in response.json():
                result[model["name"]] = {
                    "path": model["path"],
                    "sha": model["sha"],
                    "download_url": model["download_url"],
                }
        return result

    def get_tree(self):
        """
        {'cisco': {
            '2950.yaml': {'path': '', 'sha': '', 'download_url': ''}
            }
        }
        """
        result = {}
        vendors = self.get_vendors()
        for vendor in vendors:
            models = self.get_models(vendor)
            result[vendor] = models
        return result

    def get_files(self, data):
        return {}


class GitHubGQLAPI:
    tree_query = """
{
  repository(owner: "{{ owner }}", name: "{{ repo }}") {
    object(expression: "master:{{ path }}") {
      ... on Tree {
        entries {
          name
          type
        }
      }
    }
  }
}
"""
    sub_tree_query = """
{
  repository(owner: "{{ owner }}", name: "{{ repo }}") {
    object(expression: "master:{{ path }}/{{ vendor }}") {
      ... on Tree {
        entries {
          name
          type
        }
      }
    }
  }
}
"""
    file_oids_query = """
{
  repository(owner: "{{ owner }}", name: "{{ repo }}") {
    {% for file_name in file_names %}
    file_{{ loop.index0 }}: object(expression: "master:{{ path }}/{{ vendor }}/{{ file_name }}") {
      ... on Blob {
        oid
      }
    }
    {% endfor %}
  }
}
"""
    files_query = """
{
    repository(owner: "{{ owner }}", name: "{{ repo }}") {
        {% for sha, path in data.items() %}
        sha_{{ sha }}: object(expression: "master:{{ root_path }}/{{ path }}") {
            ... on Blob {
                text
            }
        }
        {% endfor %}
    }
}
"""

    def __init__(
        self,
        url="https://api.github.com/graphql",
        token=None,
        owner=None,
        repo=None,
        path="device-types",
    ):
        self.session = requests.session()
        self.session.headers.update({"Authorization": f"token {token}"})
        # Enable connection pooling and keep-alive for better performance
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=10,
            pool_maxsize=20,
            max_retries=0,  # We handle retries ourselves
        )
        self.session.mount("https://", adapter)
        self.path = path
        self.url = url
        self.token = token
        self.owner = owner
        self.repo = repo

    def get_query(self, query, max_retries=3, retry_delay=2):
        result = {}
        last_error = None

        for attempt in range(max_retries):
            try:
                response = self.session.post(url=self.url, json={"query": query})

                # Check for HTTP errors before parsing JSON
                if not response.ok:
                    if response.status_code == 502:
                        # 502 Bad Gateway - likely query too complex, retry
                        if attempt < max_retries - 1:
                            print(
                                f"      502 Bad Gateway, retrying in {retry_delay}s... (attempt {attempt + 1}/{max_retries})"
                            )
                            time.sleep(retry_delay)
                            continue
                    # For other HTTP errors, try to get the message
                    try:
                        error_data = response.json()
                        raise GQLError(
                            error_data.get("message", f"HTTP {response.status_code}")
                        )
                    except:
                        raise GQLError(
                            f"HTTP {response.status_code}: {response.text[:200]}"
                        )

                # Try to parse JSON response
                try:
                    result = response.json()
                except requests.exceptions.JSONDecodeError:
                    # If JSON parsing fails, it might be HTML error page
                    if (
                        "502 Bad Gateway" in response.text
                        or "503 Service Unavailable" in response.text
                    ):
                        if attempt < max_retries - 1:
                            print(
                                f"      Server error, retrying in {retry_delay}s... (attempt {attempt + 1}/{max_retries})"
                            )
                            time.sleep(retry_delay)
                            continue
                    raise GQLError(
                        "Can't parse message from GitHub. {}".format(
                            response.text[:500]
                        )
                    )

                # Check for GraphQL errors in response
                err = result.get("errors")
                if err:
                    error_msg = err[0].get("message")
                    # Some GraphQL errors are retryable
                    if (
                        "timeout" in error_msg.lower()
                        or "temporarily unavailable" in error_msg.lower()
                    ):
                        if attempt < max_retries - 1:
                            print(
                                f"      GraphQL error: {error_msg}, retrying in {retry_delay}s... (attempt {attempt + 1}/{max_retries})"
                            )
                            time.sleep(retry_delay)
                            continue
                    raise GQLError(message=error_msg)

                # Success!
                return result

            except GQLError:
                raise  # Re-raise GQLError as-is
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    print(
                        f"      Unexpected error: {e}, retrying in {retry_delay}s... (attempt {attempt + 1}/{max_retries})"
                    )
                    time.sleep(retry_delay)
                    continue
                else:
                    raise GQLError(f"Failed after {max_retries} attempts: {e}")

        # If we get here, all retries failed
        if last_error:
            raise GQLError(f"Failed after {max_retries} attempts: {last_error}")
        return result

    def get_tree(self, batch_size=50, delay_between_batches=0.1, verbose=True):
        """
        Fetch the device type tree from GitHub.

        Args:
            batch_size: Number of files to fetch per batch (default: 50)
            delay_between_batches: Seconds to wait between batches (default: 0.1)
            verbose: Print progress messages (default: True)

        Returns:
            Dictionary mapping vendor names to file dictionaries
        """
        result = {}

        # First, get the top-level directories (vendors)
        template = Template(self.tree_query)
        query = template.render(owner=self.owner, repo=self.repo, path=self.path)
        data = self.get_query(query)

        if not data:
            return result

        vendors = data["data"]["repository"]["object"]["entries"]

        # Pre-compile the template once (avoid repeated compilation)
        sub_template = Template(self.sub_tree_query)
        oid_template = Template(self.file_oids_query)

        total_vendors = sum(1 for v in vendors if v["type"] == "tree")
        vendor_count = 0

        for vendor in vendors:
            vendor_name = vendor["name"]

            # Skip if not a directory
            if vendor["type"] != "tree":
                continue

            vendor_count += 1
            if verbose:
                print(
                    f"Processing vendor: {vendor_name} ({vendor_count}/{total_vendors})"
                )
            result[vendor_name] = {}

            try:
                # First, get the list of file names in this vendor directory
                sub_query = sub_template.render(
                    owner=self.owner, repo=self.repo, path=self.path, vendor=vendor_name
                )
                vendor_data = self.get_query(sub_query)

                if not vendor_data:
                    if verbose:
                        print(
                            f"  Warning: No data returned for {vendor_name}, skipping..."
                        )
                    continue

                # Extract file names (not directories)
                vendor_entries = vendor_data["data"]["repository"]["object"]["entries"]
                file_names = [
                    entry["name"] for entry in vendor_entries if entry["type"] == "blob"
                ]

                if not file_names:
                    if verbose:
                        print(f"  No files found in {vendor_name}")
                    continue

                if verbose:
                    print(
                        f"  Found {len(file_names)} files, fetching OIDs in batches of {batch_size}..."
                    )

                # Now fetch OIDs in batches to avoid timeout
                failed_batches = []
                total_batches = (len(file_names) + batch_size - 1) // batch_size

                for i in range(0, len(file_names), batch_size):
                    batch = file_names[i : i + batch_size]
                    batch_num = (i // batch_size) + 1

                    if verbose:
                        print(
                            f"    Batch {batch_num}/{total_batches}: {len(batch)} files"
                        )

                    try:
                        # Query OIDs for this batch of files
                        oid_query = oid_template.render(
                            owner=self.owner,
                            repo=self.repo,
                            path=self.path,
                            vendor=vendor_name,
                            file_names=batch,
                        )
                        oid_data = self.get_query(oid_query)

                        if not oid_data:
                            if verbose:
                                print(
                                    f"      Warning: No data returned for batch {batch_num}, skipping..."
                                )
                            failed_batches.append(batch_num)
                            continue

                        # Extract OIDs and map back to file names
                        repo_data = oid_data["data"]["repository"]
                        for idx, file_name in enumerate(batch):
                            file_key = f"file_{idx}"
                            if file_key in repo_data and repo_data[file_key]:
                                result[vendor_name][file_name] = {
                                    "sha": repo_data[file_key]["oid"]
                                }

                        # Only delay if we have more batches AND delay is configured
                        if batch_num < total_batches and delay_between_batches > 0:
                            time.sleep(delay_between_batches)

                    except GQLError as e:
                        if verbose:
                            print(f"      Error fetching batch {batch_num}: {e}")
                        failed_batches.append(batch_num)
                        # Continue with the next batch instead of failing the entire vendor
                        continue

                if failed_batches and verbose:
                    print(
                        f"  Warning: Failed to fetch batches {failed_batches} for {vendor_name}"
                    )

            except GQLError as e:
                if verbose:
                    print(f"  Error processing vendor {vendor_name}: {e}")
                # Continue with the next vendor instead of failing the entire operation
                continue
            except Exception as e:
                if verbose:
                    print(f"  Unexpected error processing vendor {vendor_name}: {e}")
                continue

        return result

    def get_files(self, query_data):
        """
        data = {'sha': 'venodor/model'}
        result = {'sha': 'yaml_text'}
        """
        result = {}
        if not query_data:
            return result
        template = Template(self.files_query)
        query = template.render(
            owner=self.owner, repo=self.repo, data=query_data, root_path=self.path
        )
        data = self.get_query(query)
        for k, v in data["data"]["repository"].items():
            result[k.replace("sha_", "")] = v["text"]
        return result
