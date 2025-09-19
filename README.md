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
-   **Database**: PostgreSQL database for storing user data, site information, and accessibility reports.
-   **Scanner**: Playwright-based scanner that performs accessibility tests on web pages.
    Note: scanner container doesn't need to be run for application to work, it can be run separately as needed. The scanner is for automatic scans which happen based on the rate limit.
-   **Adminer**: A separate admin interface for managing database and setting users as admins.
-   **Deployment**: Docker and Docker Compose for easy deployment and management of the application.

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
3. Build and start the Docker containers:
    ```bash
    docker-compose up --build
    ```
4. Access the application at `http://localhost:5000`.

## Creation of users

Users can be created through the Frontend interface. When a user logs in for the first time through cas, a profile is automatically created for them. The Backend API assumes all users share the same email domain (usually the cas servers domain), which can be set in the Settings page of the Frontend. If no email domain is set, users will not be created.

## Setting a Admin User

To set a user as an admin, you can use the Adminer interface provided in the deployment. Follow these steps:

1. Login to the Frontend to automatically create a user profile.
2. Access Adminer at `http://localhost:8080`.
3. Log in using the database credentials.
4. Navigate to the `profiles` table.
5. Find the user you want to set as an admin and change the `is_admin` field to `true`.
6. Save the changes.

## Notes

-   Ensure that Backend API is not publicly accessible without proper authentication and authorization. Frontend should handle user authentication and restrict access to authorized users only.
-   The scanner can be run separately as needed and does not need to be running for the application to function. (In this case automatic scans will not happen based on the rate limit) but manual scans can still be triggered and run in the backend application.
-   Modify the `docker-compose.yml` file as needed to customize the deployment settings, such as ports, environment variables, and volume mounts.
