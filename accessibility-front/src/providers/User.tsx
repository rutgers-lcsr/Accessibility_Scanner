"use client"
import { handleRequest } from '@/lib/api';
import { User } from '@/lib/types/user';
import "@ant-design/v5-patch-for-react-19";
import { logout } from 'next-cas-client';
import { createContext, ReactNode, useContext } from 'react';
import { useAlerts } from './Alerts';

type UserContextType = {
    handlerUserApiRequest: <T>(url: string, options?: RequestInit) => Promise<T>;
};

const UserContext = createContext<UserContextType | undefined>(undefined);


type UserProviderProps = {
    children: ReactNode;
    user: User | null;
};

export const UserProvider = ({ children,user }: UserProviderProps) => {
    const { addAlert } = useAlerts();
    // Set the user if a reload is done

    const refreshLogin = async () => {
        try {
            
            // need to fix this 

            await handleRequest<{ access_token: string }>('/api/auth/refresh/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'include',
            });
        } catch {
            addAlert('Failed to refresh login', 'error');
            logout();
        }
    };

    const handlerUserApiRequest = async function <T>(
        url: string,
        options: RequestInit = {
            method: 'GET',
        }
    ) {

        if(!user) {
            throw new Error('User is not authenticated');
        }

        async function doRequest() {
            options = {
                ...options,
                headers: {
                    ...options?.headers,
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
            return await doRequest();
        } catch {
            await refreshLogin();
            // Need to get new state
            return await doRequest();
        }
    };


    return (
        <UserContext.Provider
            value={{
                handlerUserApiRequest,
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
