'use client';
import { APIError, handleRequest } from '@/lib/api';
import { User } from '@/lib/types/user';
import { useRouter } from 'next/navigation';
import { createContext, ReactNode, useContext, useEffect, useState } from 'react';

type UserContextType = {
    user: User | null;
    is_admin: boolean;
    setUser: (user: User | null) => void;
    handlerUserApiRequest: <T>(url: string, options?: RequestInit) => Promise<T>;
    login: (email: string, password: string) => Promise<true | APIError | Error>;
    logout: () => Promise<void>;
};

const UserContext = createContext<UserContextType | undefined>(undefined);

export const UserProvider = ({ children }: { children: ReactNode }) => {
    const router = useRouter();

    function getUserFromLocalStorage() {
        if (typeof window === 'undefined') return null;
        const user = window.localStorage.getItem('user');
        try {
            if (user) {
                return JSON.parse(user);
            }
        } catch (error) {
            console.error('Failed to parse user from localStorage:', error);
            return null;
        }
    }

    const [user, setUser] = useState<User | null>(getUserFromLocalStorage());

    // Set the user if a reload is done
    useEffect(() => {
        getCurrentUser();
    }, []);

    const getCurrentUser = () => {
        const user = getUserFromLocalStorage();
        if (user) {
            setUser(user);
        }
    };
    const setUserLocalStorage = (user: User | null) => {
        if (user) {
            localStorage.setItem('user', JSON.stringify(user));
        } else {
            localStorage.removeItem('user');
        }
    };

    const refreshLogin = async () => {
        const userString = localStorage.getItem('user');
        const user: User | null = userString ? JSON.parse(userString) : null;
        if (!user) {
            router.push('/login');
            return;
        }
        try {
            const response = await handleRequest<{ access_token: string }>('/api/auth/refresh', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    Authorization: `Bearer ${user?.refresh_token}`,
                },
                credentials: 'include',
            });
            user.access_token = response.access_token;
            setUser(user);
            setUserLocalStorage(user);
            return user.access_token;
        } catch (error: unknown) {
            console.error('Failed to refresh login:', error);
            logout();
            router.push('/login');
        }
    };

    const logout = async (): Promise<void> => {
        setUser(null);
        setUserLocalStorage(null);
        // Make this a request to clear cookies
        await handlerUserApiRequest<void>('/api/auth/logout', {
            method: 'POST',
        });
        window.location.reload();
        router.push('/login');
    };
    const handlerUserApiRequest = async function <T>(
        url: string,
        options: RequestInit = {
            method: 'GET',
        }
    ) {
        if (!user) {
            throw new Error('User is not authenticated');
        }
        async function doRequest(access_token: string | undefined = user?.access_token) {
            options = {
                ...options,
                headers: {
                    ...options?.headers,
                    Authorization: `Bearer ${access_token}`,
                },
            };

            const response = await handleRequest<T>(url, options);
            if (!response) {
                throw new Error('Failed to fetch user data');
            }
            return response;
        }

        // Try the request once, if it fails try refreshing the token and doing the request again
        try {
            return await doRequest(user.access_token);
        } catch {
            const newAccessToken = await refreshLogin();
            // Need to get new state
            return await doRequest(newAccessToken);
        }
    };

    const handleLogin = async (email: string, password: string) => {
        try {
            // Implement your login logic here
            const response = await handleRequest<User>('/api/auth/token', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'include', // Ensure cookies are sent with the request
                body: JSON.stringify({ email, password }),
            });

            setUser(response);
            setUserLocalStorage(response);
            window.location.reload();

            return true;
        } catch (error: unknown) {
            console.error('Login failed:', error);
            if (error instanceof APIError) {
                return error;
            }
            router.push('/login');
            return new Error('Login failed');
        }
    };

    return (
        <UserContext.Provider
            value={{
                user,
                is_admin: user?.is_admin || false,
                handlerUserApiRequest,
                setUser,
                login: handleLogin,
                logout,
            }}
        >
            {children}
        </UserContext.Provider>
    );
};

export const useUser = () => {
    const context = useContext(UserContext);
    if (!context) {
        throw new Error('useUser must be used within a UserProvider');
    }
    return context;
};
