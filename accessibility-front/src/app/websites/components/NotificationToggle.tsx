'use client';
import { Website } from '@/lib/types/website';
import { PublicUser } from '@/lib/types/user';
import { useAlerts } from '@/providers/Alerts';
import { useUser } from '@/providers/User';
import { Switch } from 'antd';
import useSWR from 'swr';
import { Legend } from './PanelFields';

type Props = {
    website: Website;
    user: PublicUser;
};

type Subscription = {
    subscribed: boolean;
    website_wide: boolean;
};

// One user's switch for this website's emails (scan finished, regressions). Independent
// of the website-wide switch that site admins control in the admin panel.
function NotificationToggle({ website, user }: Props) {
    const { handlerUserApiRequest } = useUser();
    const { addAlert } = useAlerts();
    const isMember = website.admin === user.user || website.users.includes(user.user);
    const { data, mutate, isLoading } = useSWR<Subscription>(
        isMember ? `/api/websites/${website.id}/notifications` : null,
        handlerUserApiRequest
    );

    if (!isMember || !data) return null;

    const change = async (subscribed: boolean) => {
        try {
            const updated = await handlerUserApiRequest<Subscription>(
                `/api/websites/${website.id}/notifications`,
                {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ subscribed }),
                }
            );
            mutate(updated, { revalidate: false });
            addAlert(
                subscribed
                    ? 'You will get emails about this website'
                    : 'Emails about this website are off for you',
                'success'
            );
        } catch (error) {
            addAlert('Could not update your notifications: ' + (error as Error).message, 'error');
        }
    };

    // Shown as text, not a hover tooltip, so keyboard and touch users can read it too.
    return (
        <div className="rounded-md bg-gray-50 p-4 shadow">
            <fieldset className="min-w-0">
                <Legend>Your emails</Legend>
                <div className="flex items-start gap-3 text-sm text-gray-700">
                    <Switch
                        id="notification-toggle"
                        checked={data.subscribed}
                        loading={isLoading}
                        onChange={change}
                        aria-label="Email me about this website"
                        aria-describedby="notification-toggle-help"
                    />
                    <div>
                        <label htmlFor="notification-toggle">Email me about this website</label>
                        <p
                            id="notification-toggle-help"
                            className="text-xs text-gray-500"
                            style={{ margin: '4px 0 0' }}
                        >
                            {data.website_wide
                                ? 'This website is part of your digest emails: what to fix first and what changed.'
                                : 'Email is switched off for this website by a site admin; your setting applies once it is on.'}
                        </p>
                    </div>
                </div>
            </fieldset>
        </div>
    );
}

export default NotificationToggle;
