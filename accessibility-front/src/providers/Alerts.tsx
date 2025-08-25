/*
Alerts provider using the Ant Design message component
*/
'use client';
import { message } from 'antd';
import { createContext, useContext } from 'react';

type AlertsContextType = {
    addAlert: (alert: string, type: 'success' | 'error' | 'info' | 'warning') => void;
};

export const AlertsContext = createContext<AlertsContextType | undefined>(undefined);

export const AlertsProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const [messageAPI, contextHolder] = message.useMessage();

    const addAlert = (alert: string, type: 'success' | 'error' | 'info' | 'warning') => {
        messageAPI.open({
            content: alert,
            type,
            duration: 3,
        });
    };

    return (
        <AlertsContext.Provider value={{ addAlert }}>
            {contextHolder}
            {children}
        </AlertsContext.Provider>
    );
};

export const useAlerts = () => {
    const context = useContext(AlertsContext);
    if (!context) {
        throw new Error('useAlerts must be used within an AlertsProvider');
    }
    return context;
};
