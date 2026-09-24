'use client';
import { Alert } from 'antd';

// Why the report matters, in one breath. The same text goes out in the emails
// (templates/emails/_policy.html); confirm both with the Accessibility office.
function PolicyNote() {
    return (
        <Alert
            type="info"
            showIcon
            title="Why this is required"
            description={
                <>
                    Rutgers University Policy 70.1.5 requires university websites to meet{' '}
                    <a
                        href="https://www.w3.org/WAI/WCAG21/quickref/"
                        target="_blank"
                        rel="noopener noreferrer"
                    >
                        WCAG 2.1 Level AA
                    </a>
                    . The U.S. Department of Justice&apos;s ADA Title II web accessibility rule sets
                    the same standard for public universities and has been in effect for Rutgers
                    since April 24, 2026. The issues in this report are automated checks against
                    that standard. Questions about the requirement:{' '}
                    <a href="mailto:accessibility@rutgers.edu">accessibility@rutgers.edu</a>.
                </>
            }
        />
    );
}

export default PolicyNote;
