# Accessibility Website Scanner

An accessibility website scanner built for auditing and monitoring websites for accessibility compliance issues. It helps keep track of accessibility issues over time and provides insights into the accessibility status of monitored websites.

## Features

-   Automated accessibility testing using Playwright
-   Integration with Axe for comprehensive accessibility checks
-   Reporting dashboard for tracking accessibility issues
-   Historical data tracking to monitor improvements over time through site reports

## Parts

-   **Reverse Proxy**: Nginx server acting as a reverse proxy for SSL.
-   **Backend**: Flask application handling API requests, user authentication, and database interactions.
-   **Frontend**: Nextjs application providing a user interface for managing sites, viewing reports, and configuring settings.
-   **Database**: Mariadb database for storing user data, site information, and accessibility reports.
-   **Scanner**: Celery-based background workers that perform accessibility tests on web pages using Playwright.
-   **Redis**: Message broker for Celery task queue.
-   **Flower**: Web-based monitoring tool for Celery tasks (optional).
-   **Adminer**: A separate admin interface for managing database and setting users as admins.
-   **Deployment**: Docker and Docker Compose for easy deployment and management of the application.

## Background Task Processing

The scanner uses **Celery** with Redis for background task processing.

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
4. Set up .env in `accessibility-front` directories and set the appropriate values.
   The `.env` file in `accessibility-front` should look something like this:

    ```bash
     API_URL=http://localhost:5000  # URL of the backend api e.g. http://a11y-api:5000 if using docker
     JWT_SECRET_KEY="KHJADoishdjfo" # random string
     NEXT_CAS_CLIENT_SECRET="heA1hsrnQ6mrNe7eaqxsz3i74vAKZhM0" # 32 character random string used for session encryption
     NEXT_PUBLIC_BASE_URL="http://localhost:3000" # Public URL for the frontend e.g. http://a11y.example.com
     NEXT_PUBLIC_CAS_URL="https://localhost:8443/cas" # CAS server URL
     NODE_TLS_REJECT_UNAUTHORIZED=0 # needed if using self-signed certificates for cas server
    ```

    Note: `NODE_TLS_REJECT_UNAUTHORIZED=0` is needed if using self-signed certificates for cas server.
    Furthermore, this is because docker compose requires the .env file to be in the same level as the Dockerfile file.

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

-   An admin has added a proper parent domain to the scanner. Meaning if you want to add `sub.rutgers.edu`, a admin must have added `rutgers.edu` as a parent domain first. If only `cs.rutgers.edu` is added, `sub.rutgers.edu` cannot be added.

Then, go to websites page in the Frontend and add a new website. After a site is added, depending on the settings, the scanner will automatically scan the site based on the rate limit. You can also manually trigger scans from the Frontend interface.

## Reports

Each report contains details about the accessibility issues found during the scan, along with a screenshot of the scanned page. Reports for an entire website will be aggregated and issues can will be grouped by issue type, severity, and other criteria. Its recommended to view full website reports first before diving into individual page reports.

## User Management

Any user can create an account and request a site. They will automatically be assigned to that site as an admin. Website Admins will be able to add other users to the website report but not to change ratelimits or scan the site. Website users will be able to view reports for that website but will not be able to add other users or modify the site settings. These users will also be notified when a scan is finished. Only global admins can add parent domains and websites as well as manage all users. Global admins can change the admin user of a website.

## Security

Currently the Scanner uses a custom user-agent string to identify itself to the websites it scans. Please ensure that the website allows access to the following user-agent string:

```
Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3 LCSRAccessibility/1.0
```

## Deployment using docker

The application can be deployed using Docker. A sample `docker-compose.yml` file as well as a `.env.docker.example`. For more details visit the .env.docker.example file.

## Notes

-   Ensure that Backend API is not publicly accessible without proper authentication and authorization. Frontend should handle user authentication and restrict access to authorized users only.
-   The scanner can be run separately as needed and does not need to be running for the application to function. (In this case automatic scans will not happen based on the rate limit) but manual scans can still be triggered and run in the backend application.
-   Modify the `docker-compose.yml` file as needed to customize the deployment settings, such as ports, environment variables, and volume mounts.
-   Deleting a website will also delete all associated reports and data for that website. This action is irreversible.
-   Deleting a domain will only delete a website if no other websites are using that domain as their parent domain.
-   Deleting a domain will only delete the domain itself doesnt have a parent domain it can attach to.
