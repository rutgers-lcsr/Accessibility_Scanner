'use client';
import { APIError, handleRequest } from '@/lib/api';
import { User } from '@/lib/types/user';
import '@ant-design/v5-patch-for-react-19';
import { login } from 'next-cas-client';
import { createContext, ReactNode, useContext } from 'react';

type UserContextType = {
    handlerUserApiRequest: <T>(url: string, options?: RequestInit) => Promise<T>;
};

const UserContext = createContext<UserContextType | undefined>(undefined);

type UserProviderProps = {
    children: ReactNode;
    user: User | null;
};

export const UserProvider = ({ children, user }: UserProviderProps) => {
    const handlerUserApiRequest = async function <T>(
        url: string,
        options: RequestInit = {
            method: 'GET',
        }
    ) {
        if (!user) {
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
        } catch (error) {
            // dont fail if its not 401
            if (!(error instanceof APIError)) {
                throw new Error('Unknown Error occured');
            }
            if (error.response.status === 401) {
                login();
            }
            throw error;
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
