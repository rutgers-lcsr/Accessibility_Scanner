"use client"
import { APIError, handleRequest } from '@/lib/api';
import { User } from '@/lib/types/user';
import React, { createContext, useContext, useState, ReactNode, useEffect } from 'react';


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
    const [user, setUser] = useState<User | null>(null);


    // Set the user if a reload is done 
    useEffect(() => {
        getUserFromLocalStorage();
    }, []);

    const getUserFromLocalStorage = () => {
        const user = localStorage.getItem('user');
        if (user) {
            setUser(JSON.parse(user));
        }
    };
    const setUserLocalStorage = (user: User | null) => {
        if (user) {
            localStorage.setItem('user', JSON.stringify(user));
        } else {
            localStorage.removeItem('user');
        }
    };
    const logout = () => {
        setUser(null);
        setUserLocalStorage(null);
    };
    const handlerUserApiRequest = async function <T>(url: string, options?: RequestInit) {
        if (!user) {
            throw new Error("User is not authenticated");
        }

        options = {
            ...options,
            headers: {
                ...options?.headers,
                "Authorization": `Bearer ${user?.access_token}`
            }
        };

        const response = await handleRequest<T>(url, options);
        if (!response) {
            throw new Error("Failed to fetch user data");
        }
        return response;
    }

    const handleLogin = async (email: string, password: string) => {
        try {
            // Implement your login logic here
            const response = await handleRequest<User>("/api/auth/token", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                credentials: 'include', // Ensure cookies are sent with the request
                body: JSON.stringify({ email, password }),
            });

            setUser(response);
            setUserLocalStorage(response);
            console.log(response)
            return true;
        } catch (error: unknown) {
            console.error("Login failed:", error);
            if (error instanceof APIError) {
                return error;
            }
            return new Error("Login failed");
        }

    }

    return (
        <UserContext.Provider value={{ user, is_admin: user?.is_admin || false, handlerUserApiRequest, setUser, login: handleLogin, logout }}>
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