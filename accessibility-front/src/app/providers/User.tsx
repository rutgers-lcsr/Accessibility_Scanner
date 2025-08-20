import { APIError, handleRequest } from '@/lib/api';
import { User } from '@/lib/user';
import React, { createContext, useContext, useState, ReactNode } from 'react';


type UserContextType = {
    user: User | null;
    setUser: (user: User | null) => void;
    login: (email: string, password: string) => Promise<true | APIError | Error>;
};

const UserContext = createContext<UserContextType | undefined>(undefined);

export const UserProvider = ({ children }: { children: ReactNode }) => {
    const [user, setUser] = useState<User | null>(null);


    const login = async (email: string, password: string) => {
        try {
            // Implement your login logic here
            const response = await handleRequest<User>("/api/login", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({ email, password }),
            });

            setUser(response);
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
        <UserContext.Provider value={{ user, setUser, login }}>
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