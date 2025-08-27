import { cookies } from 'next/headers';
import { User } from './types/user';

export async function getUser(): Promise<User | null> {
    const cookieStore = await cookies();
    const access_token = cookieStore.get('access_token_cookie');
    if (!access_token) return null;

    const userResponse = await fetch(`${process.env.API_URL}/api/users/me`, {
        headers: {
            cookie: `access_token_cookie=${access_token.value}`,
            Authorization: `Bearer ${access_token.value}`,
        },
    });

    if (!userResponse.ok) return null;

    return userResponse.json();
}
