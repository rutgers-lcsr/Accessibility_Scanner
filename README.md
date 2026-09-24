# Accessibility Website Scanner

An accessibility website scanner built for auditing and monitoring websites for accessibility compliance issues. It helps keep track of accessibility issues over time and provides insights into the accessibility status of monitored websites.

## Features

- Automated accessibility testing using Playwright
- Integration with Axe for comprehensive accessibility checks
- Reporting dashboard for tracking accessibility issues
- Historical data tracking to monitor improvements over time through site reports

## Parts

- **Reverse Proxy**: Nginx server acting as a reverse proxy for SSL.
- **Backend**: Flask application handling API requests, user authentication, and database interactions.
- **Frontend**: Nextjs application providing a user interface for managing sites, viewing reports, and configuring settings.
- **Database**: Mariadb database for storing user data, site information, and accessibility reports.
- **Scanner**: Celery-based background workers that perform accessibility tests on web pages using Playwright.
- **Redis**: Message broker for Celery task queue.
- **Flower**: Web-based monitoring tool for Celery tasks (optional).
- **Adminer**: A separate admin interface for managing database and setting users as admins.
- **Deployment**: Docker and Docker Compose for easy deployment and management of the application.

## Background Task Processing

The scanner uses **Celery** with Redis for background task processing. Website crawls and the
periodic tasks run on the default queue; single-page scans (the "Rescan this page" action and
quick scans) are routed to the `pages` queue so they never wait behind a crawl. In Docker,
`a11y-worker` consumes both queues and `a11y-pages-worker` only `pages`. A single local worker
must consume both:

```bash
celery -A celery_app.celery worker -Q celery,pages --concurrency=2
```

## Deployment

The application can be deployed using Docker. A sample `docker-compose.yml` file is provided for easy setup.

1. Clone the repository:
    ```bash
    git clone https://github.com/rutgers-lcsr/Accessibility_Scanner.git
    ```
2. Navigate to the project directory:
    ```bash
    cd Accessibility_Scanner
    ```
3. Set up environment variables in a `.env` file based on the provided `.env.example` file.
   `JWT_SECRET_KEY` and `INTERNAL_AUTH_SECRET` are required; the backend refuses to start
   without them. `INTERNAL_AUTH_SECRET` must also be given to the frontend, which sends it
   when logging users in so that nothing else can call the login endpoint. `SITE_ADMINS` is
   a comma-separated list of full email addresses. `ADMIN_EMAIL` and `ADMIN_PASSWORD` are
   optional; when either is unset no bootstrap admin user is created.
4. For local development without Docker, create `accessibility-front/.env` with the frontend
   values below. With Docker Compose these come from the root `.env` and nothing is copied
   into the frontend directory (its `.dockerignore` keeps env files out of the image).

    ```bash
     API_URL=http://localhost:5000  # URL of the backend api e.g. http://a11y-api:5000 if using docker
     INTERNAL_AUTH_SECRET="change-me" # must match the backend value
     NEXT_CAS_CLIENT_SECRET="heA1hsrnQ6mrNe7eaqxsz3i74vAKZhM0" # 32 character random string used for session encryption
     NEXT_PUBLIC_BASE_URL="http://localhost:3000" # Public URL for the frontend e.g. http://a11y.example.com
     NEXT_PUBLIC_CAS_URL="https://localhost:8443/cas" # CAS server URL
    ```

    Note: only for local development against a CAS server with a self-signed certificate you may add
    `NODE_TLS_REJECT_UNAUTHORIZED=0`. Never set it in production: it disables TLS verification for
    every outbound request the frontend makes.

5. Build and start the Docker containers:
    ```bash
    docker-compose up -d
    ```
6. Access the application at `http://localhost:5000`.

## Creation of users

Users can be created through the Frontend interface. When a user logs in for the first time through cas, a profile is automatically created for them. The Backend API assumes all users share the same email domain (usually the cas servers domain), which can be set in the Settings page of the Frontend. If no email domain is set, users will not be created.

## Setting a Admin User

If not set in SITEADMIN, to set a user as an admin, you can use the Adminer interface provided in the deployment. Follow these steps:

1. Login to the Frontend to automatically create a user profile.
2. Access Adminer at `http://localhost:8080`.
3. Log in using the database credentials.
4. Navigate to the `profiles` table.
5. Find the user you want to set as an admin and change the `is_admin` field to `true`.
6. Save the changes.
7. Login to the Frontend with the admin user to access admin functionalities. Note: Make sure to change initial settings like email domain before adding users.

## Setting up the first website

Websites can only be added if the following is true:

- An admin has added a proper parent domain to the scanner. Meaning if you want to add `sub.rutgers.edu`, a admin must have added `rutgers.edu` as a parent domain first. If only `cs.rutgers.edu` is added, `sub.rutgers.edu` cannot be added.

Then, go to websites page in the Frontend and add a new website. After a site is added, depending on the settings, the scanner will automatically scan the site based on the rate limit. You can also manually trigger scans from the Frontend interface.

## Reports

Each report contains details about the accessibility issues found during the scan, along with a screenshot of the scanned page. Reports for an entire website will be aggregated and issues can will be grouped by issue type, severity, and other criteria. Its recommended to view full website reports first before diving into individual page reports.

## User Management

Any user can create an account and request a site; they become that website's admin. The website admin and the users they add (members) can view its reports, triage findings, scan the website or a single page, and edit the member list and the additional start pages. All of them are emailed about the website unless they opt out. Only site admins (global admins) add parent domains, manage all users, and change a website's admin, rate limit, active and public flags, tags, categories and description.

## Security

Websites can only be added under a parent domain an admin has added, and the API and the scanner refuse to fetch any URL whose host resolves to a private, loopback, link-local or other non-public address (including redirects and page subresources), so the scanner cannot be pointed at internal services.

Currently the Scanner uses a custom user-agent string to identify itself to the websites it scans. Please ensure that the website allows access to the following user-agent string:

```
Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3 LCSRAccessibility/1.0
```

## Deployment using docker

The application can be deployed using Docker. A sample `docker-compose.yml` file as well as a `.env.docker.example`. For more details visit the .env.docker.example file.

## Maintenance commands

Run inside the API container, for example `docker compose exec a11y-api flask findings backfill`.

- `flask findings backfill [--batch 50] [--website <id>]`: creates findings (one row per failing element, tracked across scans) from the latest report of every page that has not been synced yet. Run it once after deploying the findings feature; it is safe to run again.
- `flask maintenance retention [--dry-run] [--batch 200]`: applies the report retention policy from Settings (keep `retention_keep_days` in full, one report per month up to `retention_max_days`, older ones deleted; screenshots dropped from the monthly survivors; a page's latest report is never touched). Beat runs it nightly once `retention_enabled` is true; run the dry run first and read the per-page plan.
- `flask maintenance slim-reports [--dry-run] [--batch 200]`: one-off rewrite of reports stored before slimming, dropping the node lists of passing and inapplicable rules (most of each report's size). Safe to run again.

## Documents (PDF, Word, PowerPoint, Excel)

A scan records every document a website's pages link to and, for PDFs on the website's own host, downloads up to `document_checks_per_scan` of them (each under `document_max_size_mb`) and checks whether the PDF is tagged, has a title and a language. Untagged PDFs have no reading structure for screen readers. The website page has a Documents tab; the dashboard shows documents found and untagged PDFs per website. Downloads honour `robots.txt` and the crawl delay, and are re-done every `document_recheck_days`. Documents on other hosts are listed but not fetched.

## Emails

Website owners and members get **one digest per person** covering all their websites, sent by
the daily `send_owner_digests` task only when something changed for them since their last
email (new or fixed findings, moved counts, a failed scan) or when a reminder is due. It leads
with the fixes that clear the most pages (linking the Fix first tab and the fix guides) and
says what the person fixed since last time. Nothing is sent from a scan itself.

A website with open critical or serious issues and no activity (a verdict, or something the
scanner saw fixed) for `reminder_after_days` gets a firmer reminder; after
`escalate_after_days` the website admin's copy is also sent to `escalation_email` (empty
means never). Opening the report page changes the wording but does not reset the clock. The
Owners page shows last login, last look, reminders sent and escalations. The unsubscribe link
shows a confirmation page and opts out on POST only (mail clients also get one-click
unsubscribe headers). `flask mail owner-digests --dry-run` prints who would get what;
`--user <id>` sends to one person. The site admins' weekly digest (`admin_digest_enabled`,
`DIGEST_DAY_OF_WEEK`, `DIGEST_HOUR_UTC`) is unchanged.

The emails and the website page carry a short note on why this is required (Rutgers Policy
70.1.5, WCAG 2.1 AA, the ADA Title II web rule); confirm its wording with the Accessibility
office before relying on it.

## Notes

- Ensure that Backend API is not publicly accessible without proper authentication and authorization. Frontend should handle user authentication and restrict access to authorized users only.
- The scanner can be run separately as needed and does not need to be running for the application to function. (In this case automatic scans will not happen based on the rate limit) but manual scans can still be triggered and run in the backend application.
- Modify the `docker-compose.yml` file as needed to customize the deployment settings, such as ports, environment variables, and volume mounts.
- Deleting a website will also delete all associated reports and data for that website. This action is irreversible.
- Deleting a domain will only delete a website if no other websites are using that domain as their parent domain.
- Deleting a domain will only delete the domain itself doesnt have a parent domain it can attach to.

# Change Log

## 2026-06-01

- Added API endpoint for fetching reports of websites. This adds Agentic capabilities to allow users to fetch reports through API calls and integrate with other systems or tools for further analysis and monitoring.
- Added API Keys for authentication.
